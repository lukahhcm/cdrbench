#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from cdrbench.eval.run_benchmark_score import _plot_order_drop_stop_vs_full, _read_jsonl


def _load_summary(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open('r', encoding='utf-8') as handle:
        payload = json.load(handle)
    return payload if isinstance(payload, dict) else {}


def _resolve_inputs(
    *,
    score_dir: str | None,
    scored_variants_path: str | None,
) -> tuple[Path, Path]:
    if bool(score_dir) == bool(scored_variants_path):
        raise SystemExit('Provide exactly one of --score-dir or --scored-variants-path.')

    if score_dir:
        resolved_score_dir = Path(score_dir).resolve()
        resolved_scored_variants = resolved_score_dir / 'scored_variant_predictions.jsonl'
        return resolved_score_dir, resolved_scored_variants

    resolved_scored_variants = Path(scored_variants_path).resolve()
    return resolved_scored_variants.parent, resolved_scored_variants


def _debug_filter_counts(variant_rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = {
        'total_rows': len(variant_rows),
        'passed_request_and_valid': 0,
        'track_order_sensitivity': 0,
        'reference_status_drop': 0,
        'has_distinct_full_run_reference': 0,
        'has_both_distances': 0,
    }
    for row in variant_rows:
        if bool(row.get('request_error')) or not bool(row.get('valid_prediction')):
            continue
        counts['passed_request_and_valid'] += 1

        if str(row.get('benchmark_track') or '') != 'order_sensitivity':
            continue
        counts['track_order_sensitivity'] += 1

        if str(row.get('reference_status') or '').strip().upper() != 'DROP':
            continue
        counts['reference_status_drop'] += 1

        reference_text = '' if row.get('reference_text') is None else str(row.get('reference_text'))
        full_run_text = '' if row.get('reference_text_full_run') is None else str(row.get('reference_text_full_run'))
        if not full_run_text or reference_text == full_run_text:
            continue
        counts['has_distinct_full_run_reference'] += 1

        dist_stop = row.get('edit_distance_prediction_to_reference')
        dist_full = row.get('edit_distance_prediction_to_full_run_reference')
        if dist_stop is None or dist_full is None:
            continue
        counts['has_both_distances'] += 1
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Plot stop-vs-full distance scatter for order DROP cases from scored variant predictions.'
    )
    parser.add_argument('--score-dir', default=None, help='Score directory containing scored_variant_predictions.jsonl and optional summary.json.')
    parser.add_argument('--scored-variants-path', default=None, help='Path to scored_variant_predictions.jsonl.')
    parser.add_argument('--output-dir', default=None, help='Directory to write plot/csv outputs. Defaults to the score directory.')
    parser.add_argument('--model-label', default=None, help='Optional model label override for the plot title.')
    args = parser.parse_args()

    default_output_dir, scored_variants_path = _resolve_inputs(
        score_dir=args.score_dir,
        scored_variants_path=args.scored_variants_path,
    )
    output_dir = Path(args.output_dir).resolve() if args.output_dir else default_output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    if not scored_variants_path.exists():
        raise SystemExit(f'Missing scored variant predictions: {scored_variants_path}')

    variant_rows = _read_jsonl(scored_variants_path)
    if not variant_rows:
        raise SystemExit(f'No rows found in: {scored_variants_path}')

    summary = _load_summary(default_output_dir / 'summary.json')
    if args.model_label:
        summary['model'] = args.model_label
    elif not summary.get('model'):
        summary['model'] = 'unknown-model'

    _plot_order_drop_stop_vs_full(
        output_dir=output_dir,
        variant_rows=variant_rows,
        summary=summary,
    )

    print(f'wrote plot/csv outputs -> {output_dir}', flush=True)
    debug_counts = _debug_filter_counts(variant_rows)
    print(
        'filter_counts: '
        f"total={debug_counts['total_rows']} "
        f"valid={debug_counts['passed_request_and_valid']} "
        f"order_track={debug_counts['track_order_sensitivity']} "
        f"drop={debug_counts['reference_status_drop']} "
        f"distinct_full_run={debug_counts['has_distinct_full_run_reference']} "
        f"with_distances={debug_counts['has_both_distances']}",
        flush=True,
    )
    if debug_counts['has_both_distances'] == 0:
        print(
            'No plottable rows found. Most likely causes: '
            'the file is not from order_sensitivity, '
            'these rows are not DROP cases, '
            'reference_text_full_run was not carried into scoring, '
            'or edit distances were not written for these rows.',
            flush=True,
        )
    print(
        'Diagonal y=x means equal distance to stop and full references; '
        'points below the diagonal are closer to full-run, '
        'and points above the diagonal are closer to the stopping reference.',
        flush=True,
    )


if __name__ == '__main__':
    main()
