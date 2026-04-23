#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable

import yaml

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'src'
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


TRACK_FILES = {
    'main': 'main.jsonl',
    'order_sensitivity': 'order_sensitivity.jsonl',
    'atomic_ops': 'atomic_ops.jsonl',
}

FILTER_PARAM_KEYS = {
    'alphanumeric_filter': ('min_ratio', 'max_ratio'),
    'average_line_length_filter': ('min_len', 'max_len'),
    'character_repetition_filter': ('min_ratio', 'max_ratio'),
    'flagged_words_filter': ('min_ratio', 'max_ratio'),
    'maximum_line_length_filter': ('min_len', 'max_len'),
    'special_characters_filter': ('min_ratio', 'max_ratio'),
    'stopwords_filter': ('min_ratio', 'max_ratio'),
    'text_length_filter': ('min_len', 'max_len'),
    'word_repetition_filter': ('min_ratio', 'max_ratio'),
    'words_num_filter': ('min_num', 'max_num'),
}

FILTER_DEFAULT_DIRECTION = {
    'alphanumeric_filter': 'min',
    'average_line_length_filter': 'max',
    'character_repetition_filter': 'max',
    'flagged_words_filter': 'max',
    'maximum_line_length_filter': 'max',
    'special_characters_filter': 'max',
    'stopwords_filter': 'min',
    'text_length_filter': 'min',
    'word_repetition_filter': 'max',
    'words_num_filter': 'min',
}


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open('r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def _write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + '.tmp')
    count = 0
    with tmp_path.open('w', encoding='utf-8') as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + '\n')
            count += 1
    tmp_path.replace(path)
    return count


def _load_prompt_config(path: Path) -> dict[str, Any]:
    with path.open('r', encoding='utf-8') as f:
        payload = yaml.safe_load(f)
    return payload if isinstance(payload, dict) else {}


def _humanize_operator_name(op_name: str) -> str:
    name = re.sub(r'_(mapper|filter)$', '', op_name)
    return name.replace('_', ' ')


def _format_value(value: Any) -> str:
    if isinstance(value, float):
        if abs(value) < 0.01:
            return f'{value:.4g}'
        return f'{value:g}'
    return str(value)


def _filter_condition(op_name: str, params: dict[str, Any], filter_cfg: dict[str, Any]) -> str:
    metric = str(filter_cfg.get('metric_name') or _humanize_operator_name(op_name))
    unit = filter_cfg.get('unit')
    min_key, max_key = FILTER_PARAM_KEYS.get(op_name, ('min', 'max'))
    min_value = params.get(min_key)
    max_value = params.get(max_key)
    unit_suffix = f' {unit}' if unit and unit != 'ratio' else ''

    if min_value is not None and max_value is not None:
        return (
            f'Keep the sample only if its {metric} is between '
            f'{_format_value(min_value)} and {_format_value(max_value)}{unit_suffix}.'
        )
    if min_value is not None:
        return f'Keep the sample only if its {metric} is at least {_format_value(min_value)}{unit_suffix}.'
    if max_value is not None:
        return f'Keep the sample only if its {metric} is at most {_format_value(max_value)}{unit_suffix}.'

    direction = FILTER_DEFAULT_DIRECTION.get(op_name)
    if direction == 'min':
        return f'Decide whether to keep the sample based on whether its {metric} is high enough.'
    if direction == 'max':
        return f'Decide whether to keep the sample based on whether its {metric} is low enough.'
    return str(filter_cfg.get('natural_language_intent') or f'Decide whether to keep the sample using {_humanize_operator_name(op_name)}.')


def _render_operation(
    op_name: str,
    row: dict[str, Any],
    prompt_cfg: dict[str, Any],
    *,
    include_internal_names: bool,
) -> str:
    operator_cfg = dict((prompt_cfg.get('operators') or {}).get(op_name) or {})
    filter_cfg = dict((prompt_cfg.get('filters') or {}).get(op_name) or {})
    filter_params_by_name = row.get('filter_params_by_name') if isinstance(row.get('filter_params_by_name'), dict) else {}
    params = filter_params_by_name.get(op_name) if isinstance(filter_params_by_name.get(op_name), dict) else {}

    if filter_cfg or op_name.endswith('_filter'):
        text = _filter_condition(op_name, params, filter_cfg)
    else:
        text = str(operator_cfg.get('prompt_template') or operator_cfg.get('natural_language_intent') or f'Apply {_humanize_operator_name(op_name)}.')

    text = ' '.join(text.split())
    if include_internal_names:
        return f'{text} [{op_name}]'
    return text


def _track_instruction(row: dict[str, Any]) -> str:
    track = row.get('benchmark_track')
    workflow_type = row.get('workflow_type')
    order_slot = row.get('order_slot')
    if track == 'order_sensitivity':
        return (
            f'This is an order-sensitive refinement task. The requested order is the {order_slot} variant '
            f'({workflow_type}); do not reorder the steps.'
        )
    if track == 'atomic':
        return 'This is an atomic calibration task with one isolated refinement operation.'
    if workflow_type == 'filter-then-clean':
        return 'This task first makes a keep/drop decision on the current text, then cleans kept samples.'
    if workflow_type == 'clean-then-filter':
        return 'This task first cleans the text, then makes the final keep/drop decision.'
    if workflow_type == 'clean-only':
        return 'This task only cleans or transforms the text; if the steps complete, return KEEP with the final text.'
    return 'Apply the requested data-refinement workflow exactly as written.'


def _build_user_prompt(row: dict[str, Any], prompt_cfg: dict[str, Any], *, include_internal_names: bool) -> str:
    domain_contexts = prompt_cfg.get('domain_contexts') or {}
    domain = str(row.get('domain') or 'unknown')
    scenario = str(domain_contexts.get(domain) or domain_contexts.get('atomic') or 'Perform data refinement.')
    sequence = list(row.get('operator_sequence') or [])
    if not sequence and row.get('operator'):
        sequence = [str(row['operator'])]

    rendered_steps = [
        f'{idx}. {_render_operation(op_name, row, prompt_cfg, include_internal_names=include_internal_names)}'
        for idx, op_name in enumerate(sequence, start=1)
    ]
    steps_text = '\n'.join(rendered_steps) if rendered_steps else '1. Apply the requested data refinement.'
    input_text = str(row.get('input_text', ''))

    return (
        f'{scenario}\n\n'
        f'{_track_instruction(row)}\n\n'
        'Apply the following steps exactly in order:\n'
        f'{steps_text}\n\n'
        'Filtering semantics:\n'
        '- If a keep/drop step rejects the current text, stop immediately and return DROP with an empty clean_text.\n'
        '- If all keep/drop steps pass, or if there is no keep/drop step, return KEEP with the final refined text.\n\n'
        'Output format:\n'
        'Return exactly one valid JSON object and nothing else. Use this schema:\n'
        '{"status":"KEEP","clean_text":"..."} or {"status":"DROP","clean_text":""}\n\n'
        'Raw input text:\n'
        '<<<CDR_INPUT\n'
        f'{input_text}\n'
        'CDR_INPUT>>>'
    )


def _prompt_row(
    row: dict[str, Any],
    prompt_cfg: dict[str, Any],
    *,
    prompt_style: str,
    include_internal_names: bool,
) -> dict[str, Any]:
    style_cfg = dict((prompt_cfg.get('prompt_styles') or {}).get(prompt_style) or {})
    system_prompt = str(style_cfg.get('system_prompt') or 'Follow the data-refinement request and return only JSON.')
    user_prompt = _build_user_prompt(row, prompt_cfg, include_internal_names=include_internal_names)
    messages = [
        {'role': 'system', 'content': system_prompt},
        {'role': 'user', 'content': user_prompt},
    ]
    return {
        **row,
        'prompt_id': f"{row.get('instance_id', row.get('source_record_id', 'unknown'))}::{prompt_style}",
        'prompt_style': prompt_style,
        'prompt_version': prompt_cfg.get('version', 1),
        'system_prompt': system_prompt,
        'user_prompt': user_prompt,
        'prompt': system_prompt + '\n\n' + user_prompt,
        'messages': messages,
        'expected_response_format': {
            'type': 'json_object',
            'schema_hint': '{"status":"KEEP","clean_text":"..."} or {"status":"DROP","clean_text":""}',
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description='Generate model prompts for materialized CDR-Bench instances.')
    parser.add_argument('--benchmark-dir', default='data/benchmark')
    parser.add_argument('--output-dir', default='data/benchmark_prompts')
    parser.add_argument('--prompt-config', default='configs/workflow_prompting.yaml')
    parser.add_argument('--prompt-style', default='user_natural_v1')
    parser.add_argument('--tracks', nargs='*', default=list(TRACK_FILES), choices=sorted(TRACK_FILES))
    parser.add_argument(
        '--include-internal-operator-names',
        action='store_true',
        help='Append hidden operator names to each rendered step for debugging only; do not use for headline evaluation.',
    )
    args = parser.parse_args()

    benchmark_dir = (ROOT / args.benchmark_dir).resolve()
    output_dir = (ROOT / args.output_dir).resolve()
    prompt_cfg = _load_prompt_config((ROOT / args.prompt_config).resolve())

    summary_rows = []
    for track in args.tracks:
        filename = TRACK_FILES[track]
        input_path = benchmark_dir / filename
        output_path = output_dir / filename
        if not input_path.exists():
            print(f'skip missing {track}: {input_path}', flush=True)
            continue
        rows = _read_jsonl(input_path)
        prompt_rows = [
            _prompt_row(
                row,
                prompt_cfg,
                prompt_style=args.prompt_style,
                include_internal_names=args.include_internal_operator_names,
            )
            for row in rows
        ]
        count = _write_jsonl(output_path, prompt_rows)
        summary_rows.append({'track': track, 'input_path': str(input_path), 'output_path': str(output_path), 'count': count})
        print(f'wrote {track}: {count} -> {output_path}', flush=True)

    if summary_rows:
        _write_jsonl(output_dir / 'prompt_generation_summary.jsonl', summary_rows)
        print(f'wrote summary -> {output_dir / "prompt_generation_summary.jsonl"}', flush=True)


if __name__ == '__main__':
    main()
