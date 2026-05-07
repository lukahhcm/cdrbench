#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]

TRACK_SPECS = {
    'atomic_ops': {
        'caption': 'Atomic calibration results across open- and closed-source models.',
        'label': 'tab:atomic-results-all-models',
        'columns': (
            ('mean_rs', 'RS'),
            ('mean_rs@3', 'Mean RS@3'),
            ('mean_rg', 'Mean RG'),
        ),
    },
    'main': {
        'caption': 'Main-track results across open- and closed-source models.',
        'label': 'tab:main-results-all-models',
        'columns': (
            ('mean_rs', 'RS'),
            ('mean_rs@3', 'Mean RS@3'),
            ('mean_rg', 'Mean RG'),
        ),
    },
    'order_sensitivity': {
        'caption': 'Order-sensitivity results across open- and closed-source models.',
        'label': 'tab:order-sensitivity-results-all-models',
        'columns': (
            ('mean_rs', 'RS'),
            ('mean_rs@3', 'Mean RS@3'),
            ('ocs', 'OCS'),
            ('ocs_at_k', 'OCS@K'),
            ('rs_front', 'RS Front'),
            ('rs_middle', 'RS Middle'),
            ('rs_end', 'RS End'),
        ),
    },
}

CLOSED_MODEL_PREFIXES = (
    'gpt',
    'o1',
    'o3',
    'o4',
    'claude',
    'gemini',
    'grok',
    'kimi',
    'doubao',
    'moonshot',
    'hunyuan',
)

OPEN_MODEL_PREFIXES = (
    'qwen',
    'deepseek',
    'llama',
    'mistral',
    'mixtral',
    'gemma',
    'phi',
    'yi',
    'internlm',
    'baichuan',
    'minicpm',
    'glm',
)


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


def _format_rate(value: Any, *, digits: int = 1) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return '--'
    return f'{number * 100:.{digits}f}'


def _format_rg(value: Any, *, digits: int = 3) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return '--'
    return f'{number:.{digits}f}'


def _classify_model_source(model_name: str) -> str:
    normalized = re.sub(r'[^a-z0-9]+', '', model_name.lower())
    if any(normalized.startswith(prefix) for prefix in CLOSED_MODEL_PREFIXES):
        return 'Closed'
    if any(normalized.startswith(prefix) for prefix in OPEN_MODEL_PREFIXES):
        return 'Open'
    return 'Unknown'


def _sort_value(row: dict[str, Any], metric_name: str) -> tuple[float, str]:
    try:
        metric = float(row.get(metric_name) or 0.0)
    except (TypeError, ValueError):
        metric = 0.0
    return (metric, str(row.get('model') or ''))


def _discover_track_rows(score_root: Path, track: str) -> list[dict[str, Any]]:
    rows = []
    for path in sorted(score_root.glob(f'*/{track}/paper_metrics.json')):
        payload = _load_json(path)
        if str(payload.get('track') or '') != track:
            continue
        model_name = str(payload.get('model') or path.parents[1].name)
        rows.append(
            {
                'model': model_name,
                'source': _classify_model_source(model_name),
                'mean_rs': payload.get('mean_rs'),
                'mean_rs@3': payload.get('mean_rs@3'),
                'mean_rg': payload.get('mean_rg'),
                'ocs': payload.get('ocs'),
                'ocs_at_k': payload.get('ocs_at_k'),
                'rs_front': payload.get('rs_front'),
                'rs_middle': payload.get('rs_middle'),
                'rs_end': payload.get('rs_end'),
                'source_path': str(path),
            }
        )
    return rows


def _render_metric(metric_name: str, value: Any) -> str:
    if metric_name == 'mean_rg':
        return _format_rg(value)
    return _format_rate(value)


def _render_table(
    rows: list[dict[str, Any]],
    *,
    track: str,
    caption: str,
    label: str,
) -> str:
    spec = TRACK_SPECS[track]
    metric_columns = spec['columns']
    header_cells = ['Model', 'Source', *[title for _, title in metric_columns]]
    col_spec = 'll' + ('c' * len(metric_columns))
    lines = [
        r'\begin{table*}[t]',
        r'\centering',
        rf'\caption{{{caption}}}',
        rf'\label{{{label}}}',
        rf'\begin{{tabular}}{{{col_spec}}}',
        r'\toprule',
        ' & '.join(header_cells) + r' \\',
        r'\midrule',
    ]

    for row in rows:
        rendered_metrics = [_render_metric(metric_name, row.get(metric_name)) for metric_name, _ in metric_columns]
        cells = [
            _latex_escape(str(row.get('model') or 'unknown')),
            _latex_escape(str(row.get('source') or 'Unknown')),
            *rendered_metrics,
        ]
        lines.append(' & '.join(cells) + r' \\')

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
        description='Render LaTeX result tables for the atomic_ops, main, and order_sensitivity tracks.'
    )
    parser.add_argument(
        '--score-root',
        default='data/eval_runs',
        help='Root directory containing per-run outputs such as <run_name>/<track>/paper_metrics.json.',
    )
    parser.add_argument(
        '--output-dir',
        default='data/eval_runs/reports',
        help='Directory where atomic/main/order_sensitivity LaTeX tables will be written.',
    )
    parser.add_argument(
        '--sort-by',
        default='mean_rs',
        choices=('mean_rs', 'mean_rs@3', 'mean_rg', 'ocs', 'ocs_at_k', 'model'),
        help='Primary sort key for rows inside each table.',
    )
    args = parser.parse_args()

    score_root = (ROOT / args.score_root).resolve()
    output_dir = (ROOT / args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    found_any = False
    for track, spec in TRACK_SPECS.items():
        rows = _discover_track_rows(score_root, track)
        if not rows:
            continue
        found_any = True
        if args.sort_by == 'model':
            rows.sort(key=lambda row: str(row.get('model') or ''))
        else:
            rows.sort(key=lambda row: _sort_value(row, args.sort_by), reverse=True)
        table_text = _render_table(rows, track=track, caption=spec['caption'], label=spec['label'])
        output_path = output_dir / f'{track}_results_table.tex'
        output_path.write_text(table_text, encoding='utf-8')
        print(f'wrote LaTeX table -> {output_path}', flush=True)

    if not found_any:
        raise SystemExit(f'No per-track paper_metrics.json files found under: {score_root}')


if __name__ == '__main__':
    main()
