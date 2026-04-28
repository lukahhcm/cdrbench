#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import os
import statistics
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import yaml

from cdrbench.eval.metrics import compute_workflow_metrics
from cdrbench.llm_utils import build_client, parse_json_response, resolve_api_key, resolve_base_url, resolve_model


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_PROMPT_CONFIG = ROOT / 'configs' / 'workflow_prompting.yaml'
DEFAULT_PROGRESS_EVERY = 20
LOCAL_HOSTS = {'127.0.0.1', '0.0.0.0', '::1', 'localhost'}


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open('r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + '.tmp')
    with tmp_path.open('w', encoding='utf-8') as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + '\n')
    tmp_path.replace(path)
    return len(rows)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + '.tmp')
    with tmp_path.open('w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write('\n')
    tmp_path.replace(path)


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text('', encoding='utf-8')
        return
    fieldnames: list[str] = []
    seen = set()
    for row in rows:
        for key in row:
            if key not in seen:
                seen.add(key)
                fieldnames.append(key)
    tmp_path = path.with_suffix(path.suffix + '.tmp')
    with tmp_path.open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    tmp_path.replace(path)


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open('r', encoding='utf-8') as f:
        payload = yaml.safe_load(f)
    return payload if isinstance(payload, dict) else {}


def _infer_local_api_key(base_url: str) -> str:
    host = (urlparse(base_url).hostname or '').strip().lower()
    if host in LOCAL_HOSTS:
        return 'EMPTY'
    return resolve_api_key(None)


def _resolved_api_key(explicit_api_key: str | None, base_url: str) -> str:
    if explicit_api_key:
        return explicit_api_key
    try:
        return resolve_api_key(None)
    except RuntimeError:
        return _infer_local_api_key(base_url)


def _prompt_style_config(prompt_cfg: dict[str, Any]) -> dict[str, Any]:
    prompt_styles = prompt_cfg.get('prompt_styles') or {}
    style_cfg = prompt_styles.get('user_natural_v1') or {}
    return style_cfg if isinstance(style_cfg, dict) else {}


def _default_system_prompt(prompt_cfg: dict[str, Any]) -> str:
    style_cfg = _prompt_style_config(prompt_cfg)
    prompt = style_cfg.get('system_prompt')
    if isinstance(prompt, str) and prompt.strip():
        return prompt.strip()
    return (
        'You are a careful data refinement engine. '
        'Follow the user request exactly and in order. '
        'Return only the required JSON object.'
    )


def _json_schema_hint(prompt_cfg: dict[str, Any]) -> str:
    style_cfg = _prompt_style_config(prompt_cfg)
    output_contract = style_cfg.get('output_contract') or {}
    hint = output_contract.get('json_schema_hint') if isinstance(output_contract, dict) else None
    if isinstance(hint, str) and hint.strip():
        return hint.strip()
    return '{"status":"KEEP","clean_text":"..."} or {"status":"DROP","clean_text":"..."}'


def _select_prompt_variant(row: dict[str, Any], prompt_variant_index: int) -> dict[str, Any]:
    prompt_variants = row.get('prompt_variants')
    if isinstance(prompt_variants, list) and prompt_variants:
        if prompt_variant_index < 0 or prompt_variant_index >= len(prompt_variants):
            raise IndexError(
                f'prompt_variant_index={prompt_variant_index} is out of range for '
                f'instance_id={row.get("instance_id")} with {len(prompt_variants)} variants'
            )
        selected = prompt_variants[prompt_variant_index]
        if isinstance(selected, dict):
            return selected
    user_requirement = row.get('user_requirement')
    if isinstance(user_requirement, str) and user_requirement.strip():
        return {
            'style_id': str(row.get('style_id') or 'single_prompt'),
            'style_label': str(row.get('style_label') or 'Single Prompt'),
            'user_requirement': user_requirement.strip(),
        }
    raise RuntimeError(f'No usable prompt variant found for instance_id={row.get("instance_id")}.')


def _render_user_prompt(row: dict[str, Any], user_requirement: str, schema_hint: str) -> str:
    return (
        f"Task:\n{user_requirement}\n\n"
        "Raw input text:\n"
        "<input>\n"
        f"{str(row.get('input_text', ''))}\n"
        "</input>\n\n"
        "Return JSON only.\n"
        f"Use exactly this schema: {schema_hint}\n"
        "Rules:\n"
        "- status must be KEEP or DROP.\n"
        "- If status is KEEP, clean_text must be the final refined text.\n"
        "- If status is DROP, clean_text must be the text state at the point where the sample is rejected.\n"
        "- Do not output markdown, code fences, or explanations.\n"
    )


def _chat_completion(
    *,
    client: Any,
    model: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float,
    max_tokens: int,
) -> tuple[str, dict[str, Any]]:
    request_kwargs: dict[str, Any] = {
        'model': model,
        'temperature': temperature,
        'messages': [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_prompt},
        ],
    }
    if max_tokens > 0:
        request_kwargs['max_tokens'] = max_tokens
    completion = client.chat.completions.create(**request_kwargs)
    content = completion.choices[0].message.content
    if not content:
        raise RuntimeError('LLM returned empty content.')
    usage = getattr(completion, 'usage', None)
    usage_payload = {}
    if usage is not None:
        for field in ('prompt_tokens', 'completion_tokens', 'total_tokens'):
            value = getattr(usage, field, None)
            if value is not None:
                usage_payload[field] = value
    return content, usage_payload


def _extract_prediction_payload(response_text: str) -> tuple[dict[str, Any] | None, str | None]:
    try:
        payload = parse_json_response(response_text)
    except Exception as exc:  # pragma: no cover - exercised in CLI usage
        return None, f'json_parse_error: {exc}'
    if not isinstance(payload, dict):
        return None, 'json_parse_error: response is not a JSON object'
    return payload, None


def _extract_prediction_fields(
    row: dict[str, Any],
    *,
    explicit_status_field: str | None,
    explicit_text_field: str | None,
) -> tuple[str, str]:
    candidate_objects: list[dict[str, Any]] = [row]
    for key in ('parsed_response', 'response_json', 'prediction_payload'):
        value = row.get(key)
        if isinstance(value, dict):
            candidate_objects.append(value)

    def pick(explicit: str | None, fallbacks: list[str]) -> Any:
        if explicit:
            for obj in candidate_objects:
                if explicit in obj:
                    return obj.get(explicit)
            return None
        for name in fallbacks:
            for obj in candidate_objects:
                if name in obj:
                    return obj.get(name)
        return None

    status_value = pick(explicit_status_field, ['predicted_status', 'status'])
    text_value = pick(explicit_text_field, ['predicted_clean_text', 'clean_text', 'text'])
    return ('' if status_value is None else str(status_value), '' if text_value is None else str(text_value))


def _base_score_row(
    benchmark_row: dict[str, Any],
    predicted_status: str,
    predicted_clean_text: str,
) -> dict[str, Any]:
    keep_fields = [
        'instance_id',
        'benchmark_track',
        'domain',
        'source_domain',
        'workflow_id',
        'workflow_variant_id',
        'workflow_type',
        'order_family_id',
        'order_slot',
        'order_group_instance_id',
        'group_success_rule',
        'operator',
        'operator_kind',
        'source_record_id',
        'input_text',
        'input_length_chars',
        'input_length_bucket',
        'reference_status',
        'reference_text',
    ]
    output_row = {field: benchmark_row[field] for field in keep_fields if field in benchmark_row}
    output_row['predicted_status'] = predicted_status
    output_row['predicted_clean_text'] = predicted_clean_text
    output_row.update(
        compute_workflow_metrics(
            input_text=benchmark_row.get('input_text', ''),
            reference_status=benchmark_row.get('reference_status', ''),
            reference_text=benchmark_row.get('reference_text', ''),
            predicted_status=predicted_status,
            predicted_clean_text=predicted_clean_text,
        )
    )
    return output_row


def _safe_mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _safe_median(values: list[float]) -> float:
    return statistics.median(values) if values else 0.0


def _rate(rows: list[dict[str, Any]], key: str) -> float:
    return _safe_mean([1.0 if bool(row.get(key)) else 0.0 for row in rows])


def _slice_summary(rows: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        value = str(row.get(key) or 'UNKNOWN')
        grouped.setdefault(value, []).append(row)

    summary_rows = []
    for value in sorted(grouped):
        bucket = grouped[value]
        summary_rows.append(
            {
                key: value,
                'count': len(bucket),
                'workflow_success_rate': _rate(bucket, 'workflow_success'),
                'status_accuracy': _rate(bucket, 'status_match'),
                'canonical_text_match_rate': _rate(bucket, 'text_match'),
                'avg_refinement_gain': _safe_mean([float(row.get('refinement_gain', 0.0)) for row in bucket]),
            }
        )
    return summary_rows


def _order_group_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        group_id = row.get('order_group_instance_id')
        if group_id:
            grouped.setdefault(str(group_id), []).append(row)

    results = []
    for group_id in sorted(grouped):
        bucket = grouped[group_id]
        rule = str(bucket[0].get('group_success_rule') or 'all_slots_correct')
        if rule == 'all_slots_correct':
            success = all(bool(item.get('workflow_success')) for item in bucket)
        else:
            success = all(bool(item.get('workflow_success')) for item in bucket)
        results.append(
            {
                'order_group_instance_id': group_id,
                'group_success_rule': rule,
                'slot_count': len(bucket),
                'group_success': success,
            }
        )
    return results


def _build_summary(
    rows: list[dict[str, Any]],
    *,
    track_name: str | None,
    model_name: str | None,
    base_url: str | None,
    missing_prediction_count: int = 0,
    unexpected_prediction_count: int = 0,
) -> dict[str, Any]:
    refinement_gains = [float(row.get('refinement_gain', 0.0)) for row in rows]
    input_distances = [float(row.get('edit_distance_input_to_reference', 0)) for row in rows]
    pred_distances = [float(row.get('edit_distance_prediction_to_reference', 0)) for row in rows]
    order_groups = _order_group_summary(rows)
    summary = {
        'track': track_name,
        'model': model_name,
        'base_url': base_url,
        'num_rows': len(rows),
        'missing_prediction_count': missing_prediction_count,
        'unexpected_prediction_count': unexpected_prediction_count,
        'workflow_success_rate': _rate(rows, 'workflow_success'),
        'status_accuracy': _rate(rows, 'status_match'),
        'canonical_text_match_rate': _rate(rows, 'text_match'),
        'avg_refinement_gain': _safe_mean(refinement_gains),
        'median_refinement_gain': _safe_median(refinement_gains),
        'avg_edit_distance_input_to_reference': _safe_mean(input_distances),
        'avg_edit_distance_prediction_to_reference': _safe_mean(pred_distances),
        'num_order_groups': len(order_groups),
        'order_group_success_rate': _rate(order_groups, 'group_success') if order_groups else 0.0,
        'by_operator': _slice_summary(rows, 'operator'),
        'by_domain': _slice_summary(rows, 'domain'),
        'by_source_domain': _slice_summary(rows, 'source_domain'),
        'by_reference_status': _slice_summary(rows, 'reference_status'),
    }
    return summary


def _track_name_from_path(path: Path) -> str:
    stem = path.stem
    return stem if stem else 'unknown'


def _predict(args: argparse.Namespace) -> None:
    eval_path = (ROOT / args.eval_path).resolve()
    output_path = (ROOT / args.output_path).resolve()
    output_dir = output_path.parent
    prompt_cfg = _load_yaml((ROOT / args.prompt_config).resolve())
    system_prompt = _default_system_prompt(prompt_cfg)
    schema_hint = _json_schema_hint(prompt_cfg)
    rows = _read_jsonl(eval_path)
    if args.max_samples > 0:
        rows = rows[: args.max_samples]

    base_url = resolve_base_url(args.base_url)
    api_key = _resolved_api_key(args.api_key, base_url)
    model = resolve_model(args.model)
    client = build_client(api_key=api_key, base_url=base_url)

    existing_rows: list[dict[str, Any]] = []
    done_instance_ids: set[str] = set()
    if args.resume and output_path.exists():
        existing_rows = _read_jsonl(output_path)
        done_instance_ids = {str(row.get('instance_id') or '') for row in existing_rows if row.get('instance_id')}

    output_rows = list(existing_rows)
    started = time.time()
    total_rows = len(rows)
    new_count = 0
    for index, row in enumerate(rows, start=1):
        instance_id = str(row.get('instance_id') or '')
        if instance_id and instance_id in done_instance_ids:
            continue
        prompt_variant = _select_prompt_variant(row, args.prompt_variant_index)
        user_requirement = str(prompt_variant.get('user_requirement') or '').strip()
        user_prompt = _render_user_prompt(row, user_requirement, schema_hint)

        prediction_payload = None
        prediction_error = None
        response_text = ''
        usage_payload: dict[str, Any] = {}
        for attempt in range(1, args.max_retries + 2):
            try:
                response_text, usage_payload = _chat_completion(
                    client=client,
                    model=model,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    temperature=args.temperature,
                    max_tokens=args.max_tokens,
                )
                prediction_payload, prediction_error = _extract_prediction_payload(response_text)
                if prediction_error is None:
                    break
            except Exception as exc:  # pragma: no cover - exercised in CLI usage
                prediction_error = f'request_error: {exc}'
            if attempt <= args.max_retries:
                time.sleep(args.retry_sleep_seconds)

        predicted_status = ''
        predicted_clean_text = ''
        if isinstance(prediction_payload, dict):
            predicted_status, predicted_clean_text = _extract_prediction_fields(
                {'parsed_response': prediction_payload},
                explicit_status_field=None,
                explicit_text_field=None,
            )

        scored_row = _base_score_row(row, predicted_status, predicted_clean_text)
        scored_row.update(
            {
                'prompt_variant_index': args.prompt_variant_index,
                'prompt_style_id': str(prompt_variant.get('style_id') or ''),
                'prompt_style_label': str(prompt_variant.get('style_label') or ''),
                'user_requirement': user_requirement,
                'request_model': model,
                'request_base_url': base_url,
                'raw_response': response_text,
                'parsed_response': prediction_payload,
                'prediction_error': prediction_error,
                'prediction_valid_json': prediction_error is None,
                'response_usage': usage_payload,
            }
        )
        output_rows.append(scored_row)
        if instance_id:
            done_instance_ids.add(instance_id)
        new_count += 1

        if index % args.progress_every == 0 or index == total_rows:
            elapsed = time.time() - started
            print(
                f'progress predict row={index}/{total_rows} '
                f'new={new_count} elapsed_sec={elapsed:.1f}',
                flush=True,
            )

    _write_jsonl(output_path, output_rows)
    summary = _build_summary(
        output_rows,
        track_name=_track_name_from_path(eval_path),
        model_name=model,
        base_url=base_url,
    )
    _write_json(output_dir / 'summary.json', summary)
    _write_csv(output_dir / 'by_operator.csv', summary['by_operator'])
    _write_csv(output_dir / 'by_source_domain.csv', summary['by_source_domain'])
    _write_csv(output_dir / 'by_reference_status.csv', summary['by_reference_status'])
    print(f'wrote predictions -> {output_path}', flush=True)
    print(f'wrote summary -> {output_dir / "summary.json"}', flush=True)


def _score(args: argparse.Namespace) -> None:
    predictions_path = (ROOT / args.predictions_path).resolve()
    output_dir = (ROOT / args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    prediction_rows = _read_jsonl(predictions_path)

    benchmark_rows: list[dict[str, Any]] | None = None
    if args.benchmark_path:
        benchmark_rows = _read_jsonl((ROOT / args.benchmark_path).resolve())

    if benchmark_rows is None:
        scored_rows = []
        for row in prediction_rows:
            predicted_status, predicted_clean_text = _extract_prediction_fields(
                row,
                explicit_status_field=args.prediction_status_field,
                explicit_text_field=args.prediction_text_field,
            )
            scored_row = _base_score_row(row, predicted_status, predicted_clean_text)
            passthrough = {
                key: value
                for key, value in row.items()
                if key not in scored_row
            }
            scored_row.update(passthrough)
            scored_rows.append(scored_row)
        summary = _build_summary(
            scored_rows,
            track_name=_track_name_from_path(predictions_path),
            model_name=args.model,
            base_url=args.base_url,
        )
    else:
        prediction_instance_field = args.prediction_instance_field
        prediction_map: dict[str, dict[str, Any]] = {}
        unexpected_prediction_count = 0
        for row in prediction_rows:
            instance_id = str(row.get(prediction_instance_field) or '')
            if not instance_id:
                continue
            if instance_id in prediction_map:
                raise RuntimeError(f'Duplicate prediction for instance_id={instance_id}')
            prediction_map[instance_id] = row

        benchmark_map = {str(row.get('instance_id') or ''): row for row in benchmark_rows if row.get('instance_id')}
        for instance_id in prediction_map:
            if instance_id not in benchmark_map:
                unexpected_prediction_count += 1

        scored_rows = []
        missing_prediction_count = 0
        for benchmark_row in benchmark_rows:
            instance_id = str(benchmark_row.get('instance_id') or '')
            prediction_row = prediction_map.get(instance_id)
            if prediction_row is None:
                missing_prediction_count += 1
                predicted_status = ''
                predicted_clean_text = ''
                passthrough = {'missing_prediction': True}
            else:
                predicted_status, predicted_clean_text = _extract_prediction_fields(
                    prediction_row,
                    explicit_status_field=args.prediction_status_field,
                    explicit_text_field=args.prediction_text_field,
                )
                passthrough = {
                    key: value
                    for key, value in prediction_row.items()
                    if key not in benchmark_row
                }
                passthrough['missing_prediction'] = False
            scored_row = _base_score_row(benchmark_row, predicted_status, predicted_clean_text)
            scored_row.update(passthrough)
            scored_rows.append(scored_row)

        summary = _build_summary(
            scored_rows,
            track_name=_track_name_from_path((ROOT / args.benchmark_path).resolve()),
            model_name=args.model,
            base_url=args.base_url,
            missing_prediction_count=missing_prediction_count,
            unexpected_prediction_count=unexpected_prediction_count,
        )

    _write_jsonl(output_dir / 'scored_predictions.jsonl', scored_rows)
    _write_json(output_dir / 'summary.json', summary)
    _write_csv(output_dir / 'by_operator.csv', summary['by_operator'])
    _write_csv(output_dir / 'by_domain.csv', summary['by_domain'])
    _write_csv(output_dir / 'by_source_domain.csv', summary['by_source_domain'])
    _write_csv(output_dir / 'by_reference_status.csv', summary['by_reference_status'])
    if summary.get('num_order_groups', 0):
        _write_csv(output_dir / 'order_groups.csv', _order_group_summary(scored_rows))
    print(f'wrote scored predictions -> {output_dir / "scored_predictions.jsonl"}', flush=True)
    print(f'wrote summary -> {output_dir / "summary.json"}', flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Run or score CDR-Bench evaluations. Atomic track is the initial target, but the scorer also works for main and order tracks.'
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    predict_parser = subparsers.add_parser('predict', help='Call an OpenAI-compatible API on eval-ready JSONL and save predictions.')
    predict_parser.add_argument('--eval-path', required=True, help='Eval-ready JSONL, e.g. data/benchmark_prompts/atomic_ops/eval/atomic_ops.jsonl')
    predict_parser.add_argument('--output-path', required=True, help='Prediction JSONL output path.')
    predict_parser.add_argument('--prompt-config', default=str(DEFAULT_PROMPT_CONFIG.relative_to(ROOT)))
    predict_parser.add_argument('--model', default=None)
    predict_parser.add_argument('--base-url', default=None)
    predict_parser.add_argument('--api-key', default=None)
    predict_parser.add_argument('--temperature', type=float, default=0.0)
    predict_parser.add_argument('--max-tokens', type=int, default=4096)
    predict_parser.add_argument('--prompt-variant-index', type=int, default=0)
    predict_parser.add_argument('--max-samples', type=int, default=0)
    predict_parser.add_argument('--max-retries', type=int, default=2)
    predict_parser.add_argument('--retry-sleep-seconds', type=float, default=2.0)
    predict_parser.add_argument('--progress-every', type=int, default=DEFAULT_PROGRESS_EVERY)
    predict_parser.add_argument('--resume', action='store_true')
    predict_parser.set_defaults(func=_predict)

    score_parser = subparsers.add_parser('score', help='Score existing prediction JSONL against benchmark references.')
    score_parser.add_argument('--predictions-path', required=True)
    score_parser.add_argument('--benchmark-path', default=None)
    score_parser.add_argument('--output-dir', required=True)
    score_parser.add_argument('--prediction-instance-field', default='instance_id')
    score_parser.add_argument('--prediction-status-field', default=None)
    score_parser.add_argument('--prediction-text-field', default=None)
    score_parser.add_argument('--model', default=None)
    score_parser.add_argument('--base-url', default=None)
    score_parser.set_defaults(func=_score)

    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
