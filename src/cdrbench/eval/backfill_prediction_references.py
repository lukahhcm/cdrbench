#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Iterable

from cdrbench.eval.prediction_io import ordered_prediction_row
from cdrbench.prepare_data.build_benchmark_release import RELEASE_FIELD_ORDER


REFERENCE_BACKFILL_FIELDS = [
    'reference_status',
    'reference_text',
    'reference_text_at_stop',
    'reference_text_full_run',
    'reference_trace',
    'full_run_reference_trace',
]


BENCHMARK_BACKFILL_FIELDS = [
    *RELEASE_FIELD_ORDER,
    'full_run_reference_trace',
]


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
            handle.write(json.dumps(ordered_prediction_row(row), ensure_ascii=False) + '\n')
            count += 1
    tmp_path.replace(path)
    return count


def _index_benchmark_rows(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    duplicates = 0
    for row in rows:
        instance_id = str(row.get('instance_id') or '')
        if not instance_id:
            continue
        if instance_id in indexed:
            duplicates += 1
        indexed[instance_id] = row
    if duplicates:
        print(f'warning: duplicate benchmark instance_id rows overwritten: {duplicates}', file=sys.stderr)
    return indexed


def _changed_fields(before: dict[str, Any], after: dict[str, Any], fields: list[str]) -> list[str]:
    return [field for field in fields if before.get(field) != after.get(field)]


def _backfill_rows(
    *,
    benchmark_rows: list[dict[str, Any]],
    prediction_rows: list[dict[str, Any]],
    fields: list[str],
    drop_missing: bool,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    benchmark_by_id = _index_benchmark_rows(benchmark_rows)
    output_rows: list[dict[str, Any]] = []
    matched = 0
    missing = 0
    dropped_missing = 0
    changed_rows = 0
    changed_field_counts: dict[str, int] = {}

    for row in prediction_rows:
        instance_id = str(row.get('instance_id') or '')
        benchmark_row = benchmark_by_id.get(instance_id)
        if benchmark_row is None:
            missing += 1
            if drop_missing:
                dropped_missing += 1
            else:
                output_rows.append(dict(row))
            continue

        matched += 1
        repaired = dict(row)
        before = dict(repaired)
        for field in fields:
            if field in benchmark_row:
                repaired[field] = benchmark_row[field]
        changed = _changed_fields(before, repaired, fields)
        if changed:
            changed_rows += 1
            for field in changed:
                changed_field_counts[field] = changed_field_counts.get(field, 0) + 1
        output_rows.append(repaired)

    stats = {
        'benchmark_rows': len(benchmark_rows),
        'prediction_rows': len(prediction_rows),
        'matched_by_instance_id': matched,
        'missing_in_benchmark': missing,
        'dropped_missing_in_benchmark': dropped_missing,
        'changed_rows': changed_rows,
        'changed_field_counts': changed_field_counts,
    }
    return output_rows, stats


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Backfill benchmark/GT fields from a refreshed benchmark JSONL into existing predictions by instance_id.'
    )
    parser.add_argument('--benchmark-path', required=True, help='Refreshed benchmark/release JSONL for the same track.')
    parser.add_argument('--predictions-path', required=True, help='Existing predictions JSONL to update without rerunning inference.')
    parser.add_argument('--output-path', default=None, help='Optional output path. Defaults to <predictions>.backfilled.jsonl')
    parser.add_argument('--overwrite', action='store_true', help='Overwrite predictions-path in place.')
    parser.add_argument(
        '--references-only',
        action='store_true',
        help='Only update reference_* fields. Default updates benchmark/release fields plus references.',
    )
    parser.add_argument(
        '--drop-missing',
        action='store_true',
        help='Drop prediction rows whose instance_id is not present in the refreshed benchmark.',
    )
    args = parser.parse_args()

    benchmark_path = Path(args.benchmark_path).expanduser().resolve()
    predictions_path = Path(args.predictions_path).expanduser().resolve()
    if args.overwrite and args.output_path:
        raise SystemExit('Use either --overwrite or --output-path, not both.')
    if args.overwrite:
        output_path = predictions_path
    elif args.output_path:
        output_path = Path(args.output_path).expanduser().resolve()
    else:
        output_path = predictions_path.with_name(predictions_path.stem + '.backfilled.jsonl')

    if not benchmark_path.exists():
        raise SystemExit(f'benchmark path does not exist: {benchmark_path}')
    if not predictions_path.exists():
        raise SystemExit(f'predictions path does not exist: {predictions_path}')

    fields = REFERENCE_BACKFILL_FIELDS if args.references_only else BENCHMARK_BACKFILL_FIELDS
    output_rows, stats = _backfill_rows(
        benchmark_rows=_read_jsonl(benchmark_path),
        prediction_rows=_read_jsonl(predictions_path),
        fields=fields,
        drop_missing=bool(args.drop_missing),
    )
    written = _write_jsonl(output_path, output_rows)

    print(f'benchmark_path={benchmark_path}', flush=True)
    print(f'predictions_path={predictions_path}', flush=True)
    print(f'output_path={output_path}', flush=True)
    print(f'fields_mode={"references_only" if args.references_only else "benchmark_fields"}', flush=True)
    print(
        ' '.join(
            [
                f'benchmark_rows={stats["benchmark_rows"]}',
                f'prediction_rows={stats["prediction_rows"]}',
                f'written_rows={written}',
                f'matched_by_instance_id={stats["matched_by_instance_id"]}',
                f'missing_in_benchmark={stats["missing_in_benchmark"]}',
                f'dropped_missing_in_benchmark={stats["dropped_missing_in_benchmark"]}',
                f'changed_rows={stats["changed_rows"]}',
            ]
        ),
        flush=True,
    )
    print(
        'changed_field_counts='
        + json.dumps(stats['changed_field_counts'], ensure_ascii=False, sort_keys=True),
        flush=True,
    )


if __name__ == '__main__':
    main()
