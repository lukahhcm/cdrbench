#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open('r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def _load_json(path: Path) -> dict[str, Any]:
    with path.open('r', encoding='utf-8') as f:
        payload = json.load(f)
    return payload if isinstance(payload, dict) else {}


def _latex_escape(text: str) -> str:
    replacements = {
        '\\': r'\textbackslash{}',
        '&': r'\&',
        '%': r'\%',
        '$': r'\$',
        '#': r'\#',
        '_': r'\_',
        '{': r'\{',
        '}': r'\}',
        '~': r'\textasciitilde{}',
        '^': r'\textasciicircum{}',
    }
    return ''.join(replacements.get(ch, ch) for ch in text)


def _slugify_model_name(name: str) -> str:
    slug = re.sub(r'[^A-Za-z0-9._-]+', '_', name.strip())
    return slug.strip('_') or 'unknown_model'


def _format_rate(value: Any, *, digits: int = 1) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return '--'
    return f'{number * 100:.{digits}f}'


def _discover_runs(score_root: Path) -> list[dict[str, Any]]:
    runs = []
    for path in sorted(score_root.glob('*/atomic_ops/paper_metrics.json')):
        payload = _load_json(path)
        if str(payload.get('track') or '') != 'atomic_ops':
            continue
        model = str(payload.get('model') or path.parents[1].name)
        run_root = path.parents[1]
        instance_metrics_path = run_root / 'atomic_ops' / 'instance_metrics.jsonl'
        if not instance_metrics_path.exists():
            continue
        runs.append(
            {
                'model': model,
                'model_slug': _slugify_model_name(model),
                'run_root': run_root,
                'instance_metrics_path': instance_metrics_path,
            }
        )
    return runs


def _aggregate_operator_rows(instance_rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in instance_rows:
        operator = str(row.get('operator') or '')
        if not operator:
            continue
        grouped.setdefault(operator, []).append(row)

    result = {}
    for operator, rows in grouped.items():
        operator_kind = str(rows[0].get('operator_kind') or '')
        mean_rs = sum(float(row.get('mean_rs', 0.0)) for row in rows) / len(rows)
        result[operator] = {
            'operator': operator,
            'operator_kind': operator_kind,
            'mean_rs': mean_rs,
            'count': len(rows),
        }
    return result


def _collect_operator_matrix(score_root: Path) -> tuple[list[str], list[dict[str, Any]]]:
    runs = _discover_runs(score_root)
    if not runs:
        raise SystemExit(f'No atomic runs with paper_metrics.json + instance_metrics.jsonl found under: {score_root}')

    operators: dict[str, dict[str, Any]] = {}
    for run in runs:
        operator_rows = _aggregate_operator_rows(_read_jsonl(run['instance_metrics_path']))
        run['operator_rows'] = operator_rows
        for operator, payload in operator_rows.items():
            operators.setdefault(
                operator,
                {
                    'operator': operator,
                    'operator_kind': payload.get('operator_kind'),
                },
            )

    sorted_operators = sorted(
        operators.values(),
        key=lambda item: (str(item.get('operator_kind') or ''), str(item.get('operator') or '')),
    )
    return [str(item['operator']) for item in sorted_operators], runs


def _render_operator_table(
    *,
    operators: list[str],
    runs: list[dict[str, Any]],
    operator_kind: str,
    caption: str,
    label: str,
) -> str:
    selected_operators = []
    for operator in operators:
        kinds = {
            str((run.get('operator_rows', {}).get(operator) or {}).get('operator_kind') or '')
            for run in runs
            if operator in run.get('operator_rows', {})
        }
        if operator_kind in kinds:
            selected_operators.append(operator)

    if not selected_operators:
        raise SystemExit(f'No operators found for operator_kind={operator_kind}')

    col_spec = 'l' + ('c' * len(runs))
    header_models = ' & '.join(_latex_escape(str(run['model'])) for run in runs)
    lines = [
        r'\begin{table*}[t]',
        r'\centering',
        rf'\caption{{{caption}}}',
        rf'\label{{{label}}}',
        rf'\begin{{tabular}}{{{col_spec}}}',
        r'\toprule',
        rf'Operator & {header_models} \\',
        r'\midrule',
    ]

    for operator in selected_operators:
        values = []
        for run in runs:
            payload = run.get('operator_rows', {}).get(operator)
            values.append(_format_rate((payload or {}).get('mean_rs')))
        lines.append(f"{_latex_escape(operator)} & {' & '.join(values)} \\\\")

    lines.extend(
        [
            r'\bottomrule',
            r'\end{tabular}',
            r'\end{table*}',
        ]
    )
    return '\n'.join(lines) + '\n'


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Render appendix LaTeX tables for atomic mapper/filter results by operator.'
    )
    parser.add_argument('--score-root', default='data/evaluation/score')
    parser.add_argument('--mapper-output-path', default='data/evaluation/reports/atomic_mapper_results_table.tex')
    parser.add_argument('--filter-output-path', default='data/evaluation/reports/atomic_filter_results_table.tex')
    parser.add_argument(
        '--mapper-caption',
        default='Table A1: Atomic mapper results by operator. Each cell reports RS (\\%) for one model on one mapper operator.',
    )
    parser.add_argument('--mapper-label', default='tab:atomic-mapper-results')
    parser.add_argument(
        '--filter-caption',
        default='Table A2: Atomic filter results by operator. Each cell reports RS (\\%) for one model on one filter operator.',
    )
    parser.add_argument('--filter-label', default='tab:atomic-filter-results')
    args = parser.parse_args()

    score_root = (ROOT / args.score_root).resolve()
    mapper_output_path = (ROOT / args.mapper_output_path).resolve()
    filter_output_path = (ROOT / args.filter_output_path).resolve()

    operators, runs = _collect_operator_matrix(score_root)

    mapper_table = _render_operator_table(
        operators=operators,
        runs=runs,
        operator_kind='mapper',
        caption=args.mapper_caption,
        label=args.mapper_label,
    )
    filter_table = _render_operator_table(
        operators=operators,
        runs=runs,
        operator_kind='filter',
        caption=args.filter_caption,
        label=args.filter_label,
    )

    mapper_output_path.parent.mkdir(parents=True, exist_ok=True)
    mapper_output_path.write_text(mapper_table, encoding='utf-8')
    filter_output_path.parent.mkdir(parents=True, exist_ok=True)
    filter_output_path.write_text(filter_table, encoding='utf-8')

    print(f'wrote atomic mapper LaTeX table -> {mapper_output_path}', flush=True)
    print(f'wrote atomic filter LaTeX table -> {filter_output_path}', flush=True)


if __name__ == '__main__':
    main()
