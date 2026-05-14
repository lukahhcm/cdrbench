#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import statistics
from pathlib import Path
from typing import Any, Iterable

from cdrbench.prepare_data.materialize_benchmark_instances import ROOT, _base_params, _op_kind, _operator_lookup
from cdrbench.prepare_data.materialize_domain_recipes import _apply_mapper_text, _evaluate_filter, _infer_suffix
from cdrbench.config import load_domains_config
from cdrbench.domain_assignment import build_domain_execution_plan


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open('r', encoding='utf-8') as handle:
        for line_no, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as exc:
                raise SystemExit(f'invalid JSONL in {path} at line {line_no}: {exc}') from exc
            if isinstance(payload, dict):
                rows.append(payload)
    return rows


def _write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + '.tmp')
    count = 0
    with tmp_path.open('w', encoding='utf-8') as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + '\n')
            count += 1
    tmp_path.replace(path)
    return count


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + '.tmp')
    with tmp_path.open('w', encoding='utf-8') as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write('\n')
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
    with tmp_path.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    tmp_path.replace(path)


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _median(values: list[float]) -> float:
    return statistics.median(values) if values else 0.0


def _normalize_text(value: Any) -> str:
    text = '' if value is None else str(value)
    return '\n'.join(line.rstrip() for line in text.replace('\r\n', '\n').replace('\r', '\n').strip().split('\n'))


def _instance_index(benchmark_rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for row in benchmark_rows:
        instance_id = str(row.get('instance_id') or '')
        if instance_id:
            indexed[instance_id] = row
    return indexed


def _filter_track(rows: list[dict[str, Any]], track: str) -> list[dict[str, Any]]:
    if track == 'all':
        return rows
    aliases = {'compositional': 'main'}
    wanted = aliases.get(track, track)
    return [row for row in rows if str(row.get('benchmark_track') or '') == wanted]


def _prediction_variants(row: dict[str, Any]) -> list[dict[str, Any]]:
    variants = row.get('variant_predictions')
    if isinstance(variants, list) and variants:
        return [variant for variant in variants if isinstance(variant, dict)]
    return [row]


def _variant_prediction_fields(variant: dict[str, Any]) -> tuple[bool, str, str]:
    valid_prediction = bool(
        variant.get('valid_prediction')
        if 'valid_prediction' in variant
        else variant.get('prediction_valid_json')
    )
    predicted_status = '' if variant.get('predicted_status') is None else str(variant.get('predicted_status'))
    predicted_text = '' if variant.get('predicted_clean_text') is None else str(variant.get('predicted_clean_text'))
    parsed = variant.get('parsed_response')
    if (not predicted_status or not predicted_text) and isinstance(parsed, dict):
        if not predicted_status:
            predicted_status = '' if parsed.get('status') is None else str(parsed.get('status'))
        if not predicted_text:
            predicted_text = '' if parsed.get('clean_text') is None else str(parsed.get('clean_text'))
    if predicted_status or predicted_text:
        valid_prediction = valid_prediction or (bool(predicted_status) and predicted_text != '')
    return valid_prediction, predicted_status.strip().upper(), predicted_text


def _step_trace_by_index(benchmark_row: dict[str, Any]) -> dict[int, dict[str, Any]]:
    replay = benchmark_row.get('recipe_replay')
    trace = replay.get('step_trace') if isinstance(replay, dict) else None
    if not isinstance(trace, list):
        trace = benchmark_row.get('reference_trace') if isinstance(benchmark_row.get('reference_trace'), list) else []
    indexed: dict[int, dict[str, Any]] = {}
    for item in trace:
        if not isinstance(item, dict):
            continue
        try:
            step_index = int(item.get('step_index'))
        except (TypeError, ValueError):
            continue
        indexed.setdefault(step_index, item)
    return indexed


def _operator_sequence(benchmark_row: dict[str, Any]) -> list[str]:
    replay = benchmark_row.get('recipe_replay')
    if isinstance(replay, dict) and isinstance(replay.get('operator_sequence'), list):
        return [str(item) for item in replay['operator_sequence'] if str(item).strip()]
    return [str(item) for item in benchmark_row.get('operator_sequence') or [] if str(item).strip()]


def _filter_params_by_name(benchmark_row: dict[str, Any]) -> dict[str, dict[str, Any]]:
    replay = benchmark_row.get('recipe_replay')
    if isinstance(replay, dict) and isinstance(replay.get('filter_params_by_name'), dict):
        return {str(key): dict(value) for key, value in replay['filter_params_by_name'].items() if isinstance(value, dict)}
    params = benchmark_row.get('filter_params_by_name')
    return {str(key): dict(value) for key, value in params.items() if isinstance(value, dict)} if isinstance(params, dict) else {}


def _score_operator_on_prediction(
    *,
    op_name: str,
    kind: str,
    step_index: int,
    predicted_text: str,
    predicted_status: str,
    benchmark_row: dict[str, Any],
    trace_by_step: dict[int, dict[str, Any]],
    filter_params_by_name: dict[str, dict[str, Any]],
    operators_by_name: dict[str, dict[str, Any]],
    text_match_mode: str,
    on_operator_error: str,
) -> dict[str, Any]:
    suffix = _infer_suffix(
        {
            'text': predicted_text,
            'source_name': benchmark_row.get('source_name'),
            'url': benchmark_row.get('url'),
        }
    )
    base = {
        'step_index': step_index,
        'operator': op_name,
        'kind': kind,
        'completion': False,
        'completion_basis': 'mapper_idempotence' if kind == 'mapper' else 'filter_status_match',
        'operator_error': None,
    }

    try:
        if kind == 'mapper':
            output_text, result = _apply_mapper_text(op_name, predicted_text, _base_params(op_name, operators_by_name), suffix)
            exact_unchanged = output_text == predicted_text
            norm_unchanged = _normalize_text(output_text) == _normalize_text(predicted_text)
            completed = norm_unchanged if text_match_mode == 'norm' else exact_unchanged
            base.update(
                {
                    'completion': bool(completed),
                    'exact_unchanged_after_operator': exact_unchanged,
                    'norm_unchanged_after_operator': norm_unchanged,
                    'output_length_chars': len(output_text),
                    'delta_chars': len(output_text) - len(predicted_text),
                    'operator_active_on_prediction': output_text != predicted_text,
                    'operator_result': result,
                }
            )
            return base

        params = dict(filter_params_by_name.get(op_name, _base_params(op_name, operators_by_name)))
        evaluation = _evaluate_filter(op_name, predicted_text, params, suffix)
        expected_status = str(trace_by_step.get(step_index, {}).get('status') or '').strip().upper()
        evaluated_status = str(evaluation.get('status') or '').strip().upper()
        base.update(
            {
                'completion': bool(expected_status and evaluated_status == expected_status),
                'expected_filter_status': expected_status or None,
                'evaluated_filter_status': evaluated_status or None,
                'predicted_status': predicted_status or None,
                'filter_keep': evaluation.get('keep'),
                'filter_stats': evaluation.get('stats', {}),
                'filter_params': params,
            }
        )
        return base
    except Exception as exc:
        if on_operator_error != 'continue':
            raise
        base['operator_error'] = f'{type(exc).__name__}: {exc}'
        return base


def _score_variant(
    *,
    prediction_row: dict[str, Any],
    variant: dict[str, Any],
    benchmark_row: dict[str, Any],
    operators_by_name: dict[str, dict[str, Any]],
    text_match_mode: str,
    on_operator_error: str,
) -> dict[str, Any]:
    valid_prediction, predicted_status, predicted_text = _variant_prediction_fields(variant)
    sequence = _operator_sequence(benchmark_row)
    filter_params = _filter_params_by_name(benchmark_row)
    trace_by_step = _step_trace_by_index(benchmark_row)
    operator_results = []

    if valid_prediction:
        for step_index, op_name in enumerate(sequence):
            kind = _op_kind(op_name, operators_by_name)
            operator_results.append(
                _score_operator_on_prediction(
                    op_name=op_name,
                    kind=kind,
                    step_index=step_index,
                    predicted_text=predicted_text,
                    predicted_status=predicted_status,
                    benchmark_row=benchmark_row,
                    trace_by_step=trace_by_step,
                    filter_params_by_name=filter_params,
                    operators_by_name=operators_by_name,
                    text_match_mode=text_match_mode,
                    on_operator_error=on_operator_error,
                )
            )

    completed_count = sum(1 for row in operator_results if bool(row.get('completion')))
    total_count = len(sequence)
    error_count = sum(1 for row in operator_results if row.get('operator_error'))
    return {
        'instance_id': prediction_row.get('instance_id'),
        'benchmark_track': benchmark_row.get('benchmark_track') or prediction_row.get('benchmark_track'),
        'domain': benchmark_row.get('domain') or prediction_row.get('domain'),
        'source_domain': benchmark_row.get('source_domain') or prediction_row.get('source_domain'),
        'recipe_id': benchmark_row.get('recipe_id') or prediction_row.get('recipe_id'),
        'recipe_variant_id': benchmark_row.get('recipe_variant_id') or prediction_row.get('recipe_variant_id'),
        'order_slot': benchmark_row.get('order_slot') or prediction_row.get('order_slot'),
        'operator_sequence': sequence,
        'prompt_variant_index': int(variant.get('prompt_variant_index', 0) or 0),
        'prompt_style_id': variant.get('prompt_style_id'),
        'prompt_style_label': variant.get('prompt_style_label'),
        'request_model': variant.get('request_model') or prediction_row.get('request_model'),
        'valid_prediction': valid_prediction,
        'predicted_status': predicted_status,
        'predicted_text_length_chars': len(predicted_text),
        'completed_operator_count': completed_count,
        'total_operator_count': total_count,
        'operator_progress_rate': (completed_count / total_count) if total_count else None,
        'operator_error_count': error_count,
        'operator_results': operator_results,
    }


def _flatten_operator_rows(variant_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for variant_row in variant_rows:
        for op_result in variant_row.get('operator_results', []):
            rows.append(
                {
                    'instance_id': variant_row.get('instance_id'),
                    'benchmark_track': variant_row.get('benchmark_track'),
                    'domain': variant_row.get('domain'),
                    'source_domain': variant_row.get('source_domain'),
                    'recipe_variant_id': variant_row.get('recipe_variant_id'),
                    'order_slot': variant_row.get('order_slot'),
                    'prompt_variant_index': variant_row.get('prompt_variant_index'),
                    'prompt_style_id': variant_row.get('prompt_style_id'),
                    'request_model': variant_row.get('request_model'),
                    'valid_prediction': variant_row.get('valid_prediction'),
                    **op_result,
                }
            )
    return rows


def _group_summary(rows: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        value = str(row.get(key) or 'unknown')
        grouped.setdefault(value, []).append(row)
    output = []
    for value, bucket in sorted(grouped.items()):
        completions = [1.0 if bool(row.get('completion')) else 0.0 for row in bucket]
        errors = [1.0 if row.get('operator_error') else 0.0 for row in bucket]
        output.append(
            {
                key: value,
                'count': len(bucket),
                'completion_rate': _mean(completions),
                'operator_error_rate': _mean(errors),
            }
        )
    return output


def _summary_payload(variant_rows: list[dict[str, Any]], op_rows: list[dict[str, Any]]) -> dict[str, Any]:
    valid_variant_rows = [row for row in variant_rows if bool(row.get('valid_prediction'))]
    rates = [
        float(row['operator_progress_rate'])
        for row in valid_variant_rows
        if row.get('operator_progress_rate') is not None
    ]
    return {
        'num_variants': len(variant_rows),
        'num_valid_variants': len(valid_variant_rows),
        'num_operator_checks': len(op_rows),
        'mean_operator_progress_rate': _mean(rates),
        'median_operator_progress_rate': _median(rates),
        'mean_completed_operator_count': _mean([float(row.get('completed_operator_count') or 0) for row in valid_variant_rows]),
        'mean_total_operator_count': _mean([float(row.get('total_operator_count') or 0) for row in valid_variant_rows]),
        'operator_completion_rate': _mean([1.0 if bool(row.get('completion')) else 0.0 for row in op_rows]),
        'operator_error_rate': _mean([1.0 if row.get('operator_error') else 0.0 for row in op_rows]),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Score per-operator progress by checking whether Data-Juicer operators still change model outputs.'
    )
    parser.add_argument('--benchmark-analysis-path', required=True)
    parser.add_argument('--predictions-path', required=True)
    parser.add_argument('--output-dir', required=True)
    parser.add_argument('--domains-config', default='configs/domains.yaml')
    parser.add_argument('--track', default='main', help='Track to score. Default: main. Use all to disable filtering.')
    parser.add_argument('--text-match-mode', choices=('exact', 'norm'), default='exact')
    parser.add_argument('--on-operator-error', choices=('raise', 'continue'), default='continue')
    parser.add_argument('--progress-every', type=int, default=100)
    args = parser.parse_args()

    benchmark_rows_all = _read_jsonl(Path(args.benchmark_analysis_path).resolve())
    prediction_rows_all = _read_jsonl(Path(args.predictions_path).resolve())
    benchmark_rows = _filter_track(benchmark_rows_all, str(args.track))
    prediction_rows = _filter_track(prediction_rows_all, str(args.track))
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    domains_cfg = load_domains_config(ROOT / args.domains_config)
    plan = build_domain_execution_plan(domains_cfg)
    operators_by_name = _operator_lookup(plan)
    benchmark_by_id = _instance_index(benchmark_rows)

    variant_rows = []
    missing_benchmark = 0
    total_predictions = len(prediction_rows)
    for index, prediction_row in enumerate(prediction_rows, start=1):
        instance_id = str(prediction_row.get('instance_id') or '')
        benchmark_row = benchmark_by_id.get(instance_id)
        if benchmark_row is None:
            missing_benchmark += 1
            continue
        for variant in _prediction_variants(prediction_row):
            variant_rows.append(
                _score_variant(
                    prediction_row=prediction_row,
                    variant=variant,
                    benchmark_row=benchmark_row,
                    operators_by_name=operators_by_name,
                    text_match_mode=args.text_match_mode,
                    on_operator_error=args.on_operator_error,
                )
            )
        if args.progress_every > 0 and (index % args.progress_every == 0 or index == total_predictions):
            print(
                f'progress operator-score prediction={index}/{total_predictions} '
                f'variant_rows={len(variant_rows)} missing_benchmark={missing_benchmark}',
                flush=True,
            )

    op_rows = _flatten_operator_rows(variant_rows)
    summary = _summary_payload(variant_rows, op_rows)
    summary['missing_benchmark_rows'] = missing_benchmark
    summary['track'] = args.track
    summary['num_benchmark_rows_after_track_filter'] = len(benchmark_rows)
    summary['num_prediction_rows_after_track_filter'] = len(prediction_rows)
    summary['benchmark_analysis_path'] = str(Path(args.benchmark_analysis_path).resolve())
    summary['predictions_path'] = str(Path(args.predictions_path).resolve())
    summary['text_match_mode'] = args.text_match_mode

    _write_jsonl(output_dir / 'operator_progress_variants.jsonl', variant_rows)
    _write_csv(output_dir / 'operator_progress_steps.csv', op_rows)
    _write_csv(output_dir / 'operator_progress_by_operator.csv', _group_summary(op_rows, 'operator'))
    _write_csv(output_dir / 'operator_progress_by_kind.csv', _group_summary(op_rows, 'kind'))
    _write_csv(output_dir / 'operator_progress_by_domain.csv', _group_summary(op_rows, 'domain'))
    _write_json(output_dir / 'operator_progress_summary.json', summary)

    print(f'wrote operator progress -> {output_dir}', flush=True)
    print(
        f"mean_operator_progress_rate={summary['mean_operator_progress_rate']:.4f} "
        f"operator_completion_rate={summary['operator_completion_rate']:.4f} "
        f"operator_error_rate={summary['operator_error_rate']:.4f}",
        flush=True,
    )


if __name__ == '__main__':
    main()
