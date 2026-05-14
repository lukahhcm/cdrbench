#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable

import yaml

from cdrbench.config import load_domains_config
from cdrbench.domain_assignment import build_domain_execution_plan
from cdrbench.prepare_data.materialize_benchmark_instances import (
    ROOT,
    _base_params,
    _op_kind,
    _operator_lookup,
)
from cdrbench.prepare_data.materialize_domain_recipes import (
    _apply_mapper_text,
    _infer_suffix,
)
from cdrbench.prepare_data.refresh_benchmark_references import (
    TRACK_FILENAMES,
    _load_recipe_variant_index,
    _resolve_sequence_and_filter_params,
    _resolve_track_path,
)


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


def _edit_distance(left: str, right: str) -> int:
    if left == right:
        return 0
    if len(left) < len(right):
        left, right = right, left
    previous = list(range(len(right) + 1))
    for i, left_char in enumerate(left, start=1):
        current = [i]
        for j, right_char in enumerate(right, start=1):
            insert_cost = current[j - 1] + 1
            delete_cost = previous[j] + 1
            replace_cost = previous[j - 1] + (left_char != right_char)
            current.append(min(insert_cost, delete_cost, replace_cost))
        previous = current
    return previous[-1]


def _trace_index(row: dict[str, Any]) -> dict[int, dict[str, Any]]:
    indexed: dict[int, dict[str, Any]] = {}
    traces = []
    if isinstance(row.get('full_run_reference_trace'), list):
        traces.extend(item for item in row['full_run_reference_trace'] if isinstance(item, dict))
    if isinstance(row.get('reference_trace'), list):
        traces.extend(item for item in row['reference_trace'] if isinstance(item, dict))
    for item in traces:
        try:
            step_index = int(item.get('step_index'))
        except (TypeError, ValueError):
            continue
        indexed.setdefault(step_index, item)
    return indexed


def _state_payload(
    *,
    state_index: int,
    label: str,
    text: str,
    produced_by_step_index: int | None,
    produced_by_operator: str | None,
    produced_by_kind: str | None,
    final_text: str | None,
) -> dict[str, Any]:
    return {
        'state_index': state_index,
        'label': label,
        'text': text,
        'text_length_chars': len(text),
        'produced_by_step_index': produced_by_step_index,
        'produced_by_operator': produced_by_operator,
        'produced_by_kind': produced_by_kind,
        'edit_distance_to_final': None if final_text is None else _edit_distance(text, final_text),
    }


def _replay_row(
    row: dict[str, Any],
    *,
    operators_by_name: dict[str, dict[str, Any]],
    recipe_variant_index: dict[str, dict[str, Any]],
    on_mapper_error: str,
) -> dict[str, Any]:
    sequence, filter_params_by_name, variant = _resolve_sequence_and_filter_params(row, recipe_variant_index)
    pseudo_record = {
        'text': str(row.get('input_text', '')),
        'source_name': row.get('source_name'),
        'url': row.get('url'),
    }
    suffix = _infer_suffix(pseudo_record)
    trace_by_step = _trace_index(row)
    text = str(row.get('input_text', ''))
    raw_states: list[dict[str, Any]] = [
        {
            'state_index': 0,
            'label': 't1',
            'text': text,
            'text_length_chars': len(text),
            'produced_by_step_index': None,
            'produced_by_operator': None,
            'produced_by_kind': None,
        }
    ]
    step_trace: list[dict[str, Any]] = []
    stop_text = None
    stop_step_index = None
    stop_operator = None
    replay_status = 'KEEP'

    for step_index, op_name in enumerate(sequence):
        kind = _op_kind(op_name, operators_by_name)
        input_state_index = len(raw_states) - 1
        input_text = text
        before_len = len(text)

        if kind == 'mapper':
            mapper_error = None
            params = _base_params(op_name, operators_by_name)
            try:
                text, result = _apply_mapper_text(op_name, text, params, suffix)
            except Exception as exc:
                if on_mapper_error != 'keep':
                    raise
                mapper_error = f'{type(exc).__name__}: {exc}'
                result = {
                    'active': False,
                    'skipped': 'mapper_error_keep_input',
                    'output_length': len(text),
                    'delta_chars': 0,
                }

            output_state_index = len(raw_states)
            raw_states.append(
                {
                    'state_index': output_state_index,
                    'label': f't{output_state_index + 1}',
                    'text': text,
                    'text_length_chars': len(text),
                    'produced_by_step_index': step_index,
                    'produced_by_operator': op_name,
                    'produced_by_kind': kind,
                }
            )
            step_payload = {
                'step_index': step_index,
                'operator': op_name,
                'kind': kind,
                'input_state_index': input_state_index,
                'output_state_index': output_state_index,
                'input_length_chars': before_len,
                'output_length_chars': len(text),
                'delta_chars': len(text) - before_len,
                'active': text != input_text,
                **result,
            }
            if mapper_error is not None:
                step_payload['error'] = mapper_error
            step_trace.append(step_payload)
            continue

        trace_item = trace_by_step.get(step_index, {})
        status = str(trace_item.get('status') or '').strip().upper() or 'UNKNOWN'
        keep = trace_item.get('keep')
        keep_bool = bool(keep) if keep is not None else None
        params = dict(filter_params_by_name.get(op_name, _base_params(op_name, operators_by_name)))
        if status == 'DROP' and stop_text is None:
            stop_text = text
            stop_step_index = step_index
            stop_operator = op_name
            replay_status = 'DROP'
        step_trace.append(
            {
                'step_index': step_index,
                'operator': op_name,
                'kind': kind,
                'input_state_index': input_state_index,
                'output_state_index': input_state_index,
                'input_length_chars': before_len,
                'output_length_chars': before_len,
                'delta_chars': 0,
                'status': status,
                'keep': keep_bool,
                'stats': trace_item.get('stats', {}),
                'params': params,
                'text_changed': False,
                'executed': False,
            }
        )

    final_text = text
    text_states = [
        _state_payload(
            state_index=int(state['state_index']),
            label=str(state['label']),
            text=str(state['text']),
            produced_by_step_index=state.get('produced_by_step_index'),
            produced_by_operator=state.get('produced_by_operator'),
            produced_by_kind=state.get('produced_by_kind'),
            final_text=final_text,
        )
        for state in raw_states
    ]
    replay = {
        'operator_sequence': sequence,
        'filter_params_by_name': filter_params_by_name,
        'status': replay_status,
        'stop_text': stop_text,
        'stop_step_index': stop_step_index,
        'stop_operator': stop_operator,
        'full_text': final_text,
        'full_text_length_chars': len(final_text),
        'num_text_states': len(text_states),
        'text_states': text_states,
        'step_trace': step_trace,
    }

    output = dict(row)
    output['operator_sequence'] = sequence
    output['filter_params_by_name'] = filter_params_by_name
    if variant is not None:
        output.setdefault('filter_name', variant.get('filter_name'))
        output.setdefault('recipe_type', variant.get('recipe_type') or variant.get('workflow_type'))
        output.setdefault('benchmark_track', variant.get('benchmark_track'))
        output.setdefault('order_slot', variant.get('order_slot'))
        output.setdefault('order_family_id', variant.get('order_family_id'))
    output['recipe_replay'] = replay
    output['reference_text_full_run'] = final_text
    if stop_text is not None:
        output['reference_text_at_stop'] = stop_text
    return output


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Replay selected benchmark rows and attach per-step intermediate texts for analysis.'
    )
    parser.add_argument('--benchmark-root', default='data/benchmark')
    parser.add_argument('--output-root', default='data/benchmark_analysis')
    parser.add_argument('--tracks', default='atomic_ops,main,order_sensitivity')
    parser.add_argument('--domains-config', default='configs/domains.yaml')
    parser.add_argument('--recipe-library-dir', default='data/processed/recipe_library')
    parser.add_argument('--on-mapper-error', choices=('raise', 'keep'), default='raise')
    args = parser.parse_args()

    benchmark_root = (ROOT / args.benchmark_root).resolve()
    output_root = (ROOT / args.output_root).resolve()
    recipe_library_dir = (ROOT / args.recipe_library_dir).resolve()
    track_names = [item.strip() for item in str(args.tracks).split(',') if item.strip()]
    unsupported = [track for track in track_names if track not in TRACK_FILENAMES]
    if unsupported:
        raise SystemExit(f'unsupported tracks: {", ".join(unsupported)}')

    domains_cfg = load_domains_config(ROOT / args.domains_config)
    plan = build_domain_execution_plan(domains_cfg)
    operators_by_name = _operator_lookup(plan)
    recipe_variant_index = _load_recipe_variant_index(recipe_library_dir)
    summary: dict[str, Any] = {'benchmark_root': str(benchmark_root), 'output_root': str(output_root), 'tracks': {}}

    for track in track_names:
        input_path = _resolve_track_path(benchmark_root, track)
        rows = _read_jsonl(input_path)
        replayed_rows = []
        status_counts = {'KEEP': 0, 'DROP': 0, 'UNKNOWN': 0}
        for index, row in enumerate(rows, start=1):
            try:
                replayed = _replay_row(
                    row,
                    operators_by_name=operators_by_name,
                    recipe_variant_index=recipe_variant_index,
                    on_mapper_error=args.on_mapper_error,
                )
            except Exception as exc:
                raise SystemExit(
                    f'failed to replay track={track} instance_id={row.get("instance_id")} row_index={index}: {exc}'
                ) from exc
            status = str(replayed.get('recipe_replay', {}).get('status') or 'UNKNOWN')
            status_counts[status if status in status_counts else 'UNKNOWN'] += 1
            replayed_rows.append(replayed)

        relative_parent = input_path.parent.relative_to(benchmark_root) if input_path.parent != benchmark_root else Path()
        output_path = output_root / relative_parent / input_path.name
        count = _write_jsonl(output_path, replayed_rows)
        summary['tracks'][track] = {
            'input_path': str(input_path),
            'output_path': str(output_path),
            'rows': count,
            'replay_status_counts': status_counts,
        }
        print(f'replayed {track}: rows={count} -> {output_path}', flush=True)

    _write_json(output_root / 'replay_summary.json', summary)
    print(f'wrote summary -> {output_root / "replay_summary.json"}', flush=True)


if __name__ == '__main__':
    main()
