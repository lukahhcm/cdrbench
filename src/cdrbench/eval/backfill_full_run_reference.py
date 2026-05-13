#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


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


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + '.tmp')
    with tmp_path.open('w', encoding='utf-8') as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + '\n')
    tmp_path.replace(path)


def _first_non_empty(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text if text else None


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Backfill reference_text_full_run from benchmark rows into existing predictions by instance_id.'
    )
    parser.add_argument('--benchmark-path', required=True, help='Path to benchmark JSONL (typically order_sensitivity benchmark file).')
    parser.add_argument('--predictions-path', required=True, help='Path to existing predictions JSONL to repair.')
    parser.add_argument('--output-path', default=None, help='Optional output path. Defaults to <predictions>.with_full_run.jsonl')
    parser.add_argument('--overwrite', action='store_true', help='Overwrite predictions-path in place.')
    args = parser.parse_args()

    benchmark_path = Path(args.benchmark_path).resolve()
    predictions_path = Path(args.predictions_path).resolve()
    if args.overwrite and args.output_path:
        raise SystemExit('Use either --overwrite or --output-path, not both.')

    if args.overwrite:
        output_path = predictions_path
    elif args.output_path:
        output_path = Path(args.output_path).resolve()
    else:
        output_path = predictions_path.with_name(predictions_path.stem + '.with_full_run.jsonl')

    benchmark_rows = _read_jsonl(benchmark_path)
    prediction_rows = _read_jsonl(predictions_path)

    benchmark_index: dict[str, dict[str, Any]] = {}
    benchmark_with_full = 0
    for row in benchmark_rows:
        instance_id = str(row.get('instance_id') or '')
        if not instance_id:
            continue
        benchmark_index[instance_id] = row
        if _first_non_empty(row.get('reference_text_full_run')) is not None:
            benchmark_with_full += 1

    updated_rows: list[dict[str, Any]] = []
    matched = 0
    filled = 0
    already_present = 0
    missing_in_benchmark = 0
    missing_full_run_in_benchmark = 0

    for row in prediction_rows:
        repaired = dict(row)
        instance_id = str(row.get('instance_id') or '')
        benchmark_row = benchmark_index.get(instance_id)
        if benchmark_row is None:
            missing_in_benchmark += 1
            updated_rows.append(repaired)
            continue

        matched += 1
        existing_full_run = _first_non_empty(repaired.get('reference_text_full_run'))
        benchmark_full_run = _first_non_empty(benchmark_row.get('reference_text_full_run'))
        benchmark_full_trace = benchmark_row.get('full_run_reference_trace')

        if existing_full_run is not None:
            already_present += 1
        elif benchmark_full_run is not None:
            repaired['reference_text_full_run'] = benchmark_full_run
            if benchmark_full_trace is not None and 'full_run_reference_trace' not in repaired:
                repaired['full_run_reference_trace'] = benchmark_full_trace
            filled += 1
        else:
            missing_full_run_in_benchmark += 1

        updated_rows.append(repaired)

    _write_jsonl(output_path, updated_rows)

    print(f'benchmark_rows={len(benchmark_rows)} benchmark_with_full_run={benchmark_with_full}', flush=True)
    print(f'prediction_rows={len(prediction_rows)} matched_by_instance_id={matched}', flush=True)
    print(
        f'filled_reference_text_full_run={filled} '
        f'already_present={already_present} '
        f'missing_in_benchmark={missing_in_benchmark} '
        f'missing_full_run_in_benchmark={missing_full_run_in_benchmark}',
        flush=True,
    )
    print(f'wrote repaired predictions -> {output_path}', flush=True)


if __name__ == '__main__':
    main()
