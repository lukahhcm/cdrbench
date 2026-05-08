#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open('r', encoding='utf-8') as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + '.tmp')
    with tmp_path.open('w', encoding='utf-8') as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + '\n')
    tmp_path.replace(path)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open('r', encoding='utf-8', newline='') as handle:
        return list(csv.DictReader(handle))


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


def _read_text_lines(path: Path) -> list[str]:
    lines = []
    with path.open('r', encoding='utf-8') as handle:
        for line in handle:
            text = line.strip()
            if not text or text.startswith('#'):
                continue
            lines.append(text)
    return lines


def _to_int(value: Any) -> int:
    if value is None:
        return 0
    text = str(value).strip()
    if not text:
        return 0
    return int(float(text))


def _prompt_variant_count(row: dict[str, Any]) -> int:
    variants = row.get('prompt_variants')
    if isinstance(variants, list):
        return len(variants)
    return 0


def _row_sort_key(row: dict[str, Any]) -> tuple[str, str]:
    return (str(row.get('source_record_id') or ''), str(row.get('instance_id') or ''))


def _take_balanced_rows(rows: list[dict[str, Any]], max_rows: int) -> list[dict[str, Any]]:
    if len(rows) <= max_rows:
        return sorted(rows, key=_row_sort_key)

    ordered = sorted(rows, key=_row_sort_key)
    keep_rows = [row for row in ordered if str(row.get('reference_status') or '').upper() == 'KEEP']
    drop_rows = [row for row in ordered if str(row.get('reference_status') or '').upper() == 'DROP']
    other_rows = [
        row for row in ordered if str(row.get('reference_status') or '').upper() not in {'KEEP', 'DROP'}
    ]

    if not keep_rows or not drop_rows:
        return ordered[:max_rows]

    target_keep = max_rows // 2
    target_drop = max_rows // 2
    selected = [*keep_rows[:target_keep], *drop_rows[:target_drop]]

    keep_remaining = keep_rows[target_keep:]
    drop_remaining = drop_rows[target_drop:]
    if max_rows % 2 == 1:
        if len(keep_remaining) >= len(drop_remaining) and keep_remaining:
            selected.append(keep_remaining[0])
            keep_remaining = keep_remaining[1:]
        elif drop_remaining:
            selected.append(drop_remaining[0])
            drop_remaining = drop_remaining[1:]

    remainder = [*keep_remaining, *drop_remaining, *other_rows]
    if len(selected) < max_rows:
        selected.extend(remainder[: max_rows - len(selected)])

    return sorted(selected[:max_rows], key=_row_sort_key)


def _resolve_source_file(source_dir: Path, filename: str) -> Path:
    direct = source_dir / filename
    if direct.exists():
        return direct
    fallback = source_dir.parent / filename
    if fallback.exists():
        return fallback
    raise SystemExit(f'missing required source file: expected {direct} or {fallback}')


def _resolve_optional_file(base_dir: Path, filename: str) -> Path | None:
    candidate = base_dir / filename
    return candidate if candidate.exists() else None


def _prediction_row_has_compliance_failure(row: dict[str, Any]) -> bool:
    for variant in row.get('variant_predictions') or []:
        if not isinstance(variant, dict):
            continue
        prediction_error = str(variant.get('prediction_error') or '')
        raw_response = str(variant.get('raw_response') or '')
        if prediction_error.startswith('non_scoring_refusal:'):
            return True
        if 'data_inspection_failed' in prediction_error or 'data_inspection_failed' in raw_response:
            return True
        if 'inappropriate content' in prediction_error.lower() or 'inappropriate content' in raw_response.lower():
            return True
    return False


def _load_excluded_instance_ids(
    manual_ids: list[str],
    ids_file: Path | None,
    predictions_path: Path | None,
) -> set[str]:
    excluded = {text.strip() for text in manual_ids if str(text).strip()}
    if ids_file is not None:
        for line in _read_text_lines(ids_file):
            excluded.add(line)
    if predictions_path is not None:
        for row in _read_jsonl(predictions_path):
            instance_id = str(row.get('instance_id') or '').strip()
            if instance_id and _prediction_row_has_compliance_failure(row):
                excluded.add(instance_id)
    return excluded


def _operator_rank_key(row: dict[str, Any]) -> tuple[int, int, int, str]:
    return (
        _to_int(row.get('selected_count')),
        _to_int(row.get('candidate_count')),
        _to_int(row.get('keep_count')) + _to_int(row.get('drop_count')),
        str(row.get('operator') or ''),
    )


def _summary_manifest(summary_rows: list[dict[str, str]]) -> dict[str, dict[str, Any]]:
    manifest: dict[str, dict[str, Any]] = {}
    for row in summary_rows:
        operator = str(row.get('operator') or '').strip()
        if not operator:
            continue
        best = manifest.get(operator)
        if best is None or _operator_rank_key(row) > _operator_rank_key(best):
            manifest[operator] = {
                'operator': operator,
                'operator_kind': row.get('operator_kind'),
                'candidate_count': _to_int(row.get('candidate_count')),
                'full_selected_count': _to_int(row.get('selected_count')),
                'keep_count': _to_int(row.get('keep_count') or row.get('selected_keep_count')),
                'drop_count': _to_int(row.get('drop_count') or row.get('selected_drop_count')),
            }
    return manifest


def _rows_manifest(full_rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    by_operator: dict[str, list[dict[str, Any]]] = defaultdict(list)
    meta: dict[str, dict[str, Any]] = {}
    for row in full_rows:
        operator = str(row.get('operator') or '').strip()
        if not operator:
            continue
        by_operator[operator].append(row)
        meta.setdefault(operator, {'operator': operator, 'operator_kind': row.get('operator_kind')})
    manifest: dict[str, dict[str, Any]] = {}
    for operator, rows in by_operator.items():
        manifest[operator] = {
            **meta[operator],
            'full_selected_count': len(rows),
            'keep_count': sum(1 for row in rows if str(row.get('reference_status') or '').upper() == 'KEEP'),
            'drop_count': sum(1 for row in rows if str(row.get('reference_status') or '').upper() == 'DROP'),
        }
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description='Build a smaller engineering subset from the full atomic benchmark.')
    parser.add_argument('--source-dir', default='data/benchmark_full/atomic_ops')
    parser.add_argument('--output-dir', default='data/benchmark/atomic_ops')
    parser.add_argument('--processed-summary-dir', default='data/processed/benchmark_instances')
    parser.add_argument('--rows-per-operator', type=int, default=6)
    parser.add_argument('--min-prompt-variants', type=int, default=0)
    parser.add_argument('--exclude-instance-id', action='append', default=[])
    parser.add_argument('--exclude-instance-ids-file', default=None)
    parser.add_argument('--exclude-predictions-path', default=None)
    args = parser.parse_args()

    source_dir = Path(args.source_dir).resolve()
    output_dir = Path(args.output_dir).resolve()
    processed_summary_dir = Path(args.processed_summary_dir).resolve()
    exclude_instance_ids_file = Path(args.exclude_instance_ids_file).resolve() if args.exclude_instance_ids_file else None
    exclude_predictions_path = Path(args.exclude_predictions_path).resolve() if args.exclude_predictions_path else None
    if args.rows_per_operator <= 0:
        raise SystemExit('--rows-per-operator must be > 0')
    if args.min_prompt_variants < 0:
        raise SystemExit('--min-prompt-variants must be >= 0')

    atomic_path = _resolve_source_file(source_dir, 'atomic_ops.jsonl')
    full_rows = _read_jsonl(atomic_path)
    if args.min_prompt_variants > 0:
        full_rows = [
            row for row in full_rows if _prompt_variant_count(row) >= args.min_prompt_variants
        ]
    excluded_instance_ids = _load_excluded_instance_ids(
        manual_ids=list(args.exclude_instance_id),
        ids_file=exclude_instance_ids_file,
        predictions_path=exclude_predictions_path,
    )

    summary_path = _resolve_optional_file(processed_summary_dir, 'atomic_ops_summary.csv')
    manifest_by_operator = {}
    if args.min_prompt_variants <= 0 and summary_path is not None:
        manifest_by_operator = _summary_manifest(_read_csv(summary_path))
    if not manifest_by_operator:
        manifest_by_operator = _rows_manifest(full_rows)
    if not manifest_by_operator:
        raise SystemExit(f'no usable atomic operators found in {atomic_path}')

    rows_by_operator: dict[str, list[dict[str, Any]]] = defaultdict(list)
    excluded_by_operator: dict[str, int] = defaultdict(int)
    for row in full_rows:
        operator = str(row.get('operator') or '')
        if operator not in manifest_by_operator:
            continue
        instance_id = str(row.get('instance_id') or '').strip()
        if instance_id in excluded_instance_ids:
            excluded_by_operator[operator] += 1
            continue
        rows_by_operator[operator].append(row)

    subset_rows: list[dict[str, Any]] = []
    manifest_rows: list[dict[str, Any]] = []
    for operator in sorted(manifest_by_operator):
        sampled_rows = _take_balanced_rows(rows_by_operator.get(operator, []), args.rows_per_operator)
        if args.min_prompt_variants > 0 and not sampled_rows:
            continue
        subset_rows.extend(sampled_rows)
        meta = manifest_by_operator[operator]
        manifest_rows.append(
            {
                **meta,
                'subset_selected_count': len(sampled_rows),
                'subset_keep_count': sum(
                    1 for row in sampled_rows if str(row.get('reference_status') or '').upper() == 'KEEP'
                ),
                'subset_drop_count': sum(
                    1 for row in sampled_rows if str(row.get('reference_status') or '').upper() == 'DROP'
                ),
                'excluded_instance_count': excluded_by_operator.get(operator, 0),
                'eligible_candidate_count': len(rows_by_operator.get(operator, [])),
                'min_prompt_variants': args.min_prompt_variants,
            }
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    _write_jsonl(output_dir / 'atomic_ops.jsonl', subset_rows)
    _write_csv(output_dir / 'atomic_ops_summary.csv', manifest_rows)
    _write_csv(output_dir / 'selected_operators.csv', manifest_rows)

    print(
        f'wrote engineering atomic subset: operators={len(manifest_rows)} rows={len(subset_rows)} '
        f'excluded_instances={len(excluded_instance_ids)} -> {output_dir / "atomic_ops.jsonl"}',
        flush=True,
    )
    print(f'wrote subset summary -> {output_dir / "atomic_ops_summary.csv"}', flush=True)
    print(f'wrote selected operators manifest -> {output_dir / "selected_operators.csv"}', flush=True)


if __name__ == '__main__':
    main()
