#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


ORDER_SLOTS = ('front', 'middle', 'end')
TRACK_CONFIGS = {
    'atomic_ops': {
        'data_file': 'atomic_ops.jsonl',
        'summary_file': 'atomic_ops_summary.csv',
        'manifest_file': 'selected_operators.csv',
        'selection_field': 'operator',
        'mode': 'row',
    },
    'main': {
        'data_file': 'main.jsonl',
        'summary_file': 'main_summary.csv',
        'manifest_file': 'selected_variants.csv',
        'selection_field': 'recipe_variant_id',
        'mode': 'row',
    },
    'order_sensitivity': {
        'data_file': 'order_sensitivity.jsonl',
        'summary_file': 'order_sensitivity_summary.csv',
        'manifest_file': 'selected_families.csv',
        'selection_field': 'order_family_id',
        'mode': 'group',
    },
}


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
    values = []
    with path.open('r', encoding='utf-8') as handle:
        for line in handle:
            text = line.strip()
            if not text or text.startswith('#'):
                continue
            values.append(text)
    return values


def _resolve_file(base_dir: Path, filename: str) -> Path:
    direct = base_dir / filename
    if direct.exists():
        return direct
    fallback = base_dir.parent / filename
    if fallback.exists():
        return fallback
    raise SystemExit(f'missing required file: expected {direct} or {fallback}')


def _resolve_optional_file(base_dir: Path, filename: str) -> Path | None:
    direct = base_dir / filename
    if direct.exists():
        return direct
    fallback = base_dir.parent / filename
    if fallback.exists():
        return fallback
    return None


def _row_sort_key(row: dict[str, Any]) -> tuple[str, str]:
    return (str(row.get('source_record_id') or ''), str(row.get('instance_id') or ''))


def _group_sort_key(rows: list[dict[str, Any]]) -> tuple[str, str]:
    source_record_id = ''
    group_id = ''
    for row in rows:
        if not source_record_id:
            source_record_id = str(row.get('source_record_id') or '')
        if not group_id:
            group_id = str(row.get('order_group_instance_id') or '')
    return source_record_id, group_id


def _normalize_group_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]] | None:
    by_slot = {str(row.get('order_slot') or ''): row for row in rows}
    if set(by_slot) != set(ORDER_SLOTS):
        return None
    return [by_slot['front'], by_slot['middle'], by_slot['end']]


def _prediction_row_has_compliance_failure(row: dict[str, Any]) -> bool:
    for variant in row.get('variant_predictions') or []:
        if not isinstance(variant, dict):
            continue
        prediction_error = str(variant.get('prediction_error') or '')
        raw_response = str(variant.get('raw_response') or '')
        lowered_error = prediction_error.lower()
        lowered_raw = raw_response.lower()
        if prediction_error.startswith('non_scoring_refusal:'):
            return True
        if 'data_inspection_failed' in prediction_error or 'data_inspection_failed' in raw_response:
            return True
        if 'inappropriate content' in lowered_error or 'inappropriate content' in lowered_raw:
            return True
        if '内容不合规' in prediction_error or '内容不合规' in raw_response:
            return True
        if '输入不合规' in prediction_error or '输入不合规' in raw_response:
            return True
    return False


def _load_bad_instance_ids(
    manual_ids: list[str],
    ids_file: Path | None,
    predictions_path: Path | None,
) -> set[str]:
    bad_ids = {str(value).strip() for value in manual_ids if str(value).strip()}
    if ids_file is not None:
        bad_ids.update(_read_text_lines(ids_file))
    if predictions_path is not None:
        for row in _read_jsonl(predictions_path):
            instance_id = str(row.get('instance_id') or '').strip()
            if instance_id and _prediction_row_has_compliance_failure(row):
                bad_ids.add(instance_id)
    return bad_ids


def _replace_row_track(
    benchmark_rows: list[dict[str, Any]],
    full_rows: list[dict[str, Any]],
    bad_ids: set[str],
    selection_field: str,
) -> list[dict[str, Any]]:
    full_by_selection: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in full_rows:
        full_by_selection[str(row.get(selection_field) or '')].append(row)

    selected_instance_ids = {
        str(row.get('instance_id') or '').strip()
        for row in benchmark_rows
        if str(row.get('instance_id') or '').strip()
    }
    updated_rows = list(benchmark_rows)
    unresolved_bad_ids: list[str] = []

    for index, row in enumerate(benchmark_rows):
        instance_id = str(row.get('instance_id') or '').strip()
        if instance_id not in bad_ids:
            continue
        selection_value = str(row.get(selection_field) or '')
        current_key = _row_sort_key(row)
        ordered_candidates = sorted(full_by_selection.get(selection_value, []), key=_row_sort_key)
        later = []
        earlier = []
        for candidate in ordered_candidates:
            candidate_id = str(candidate.get('instance_id') or '').strip()
            if (
                not candidate_id
                or candidate_id == instance_id
                or candidate_id in bad_ids
                or candidate_id in selected_instance_ids
            ):
                continue
            if _row_sort_key(candidate) > current_key:
                later.append(candidate)
            else:
                earlier.append(candidate)
        replacement = later[0] if later else (earlier[0] if earlier else None)
        if replacement is None:
            unresolved_bad_ids.append(instance_id)
            continue
        replacement_id = str(replacement.get('instance_id') or '').strip()
        selected_instance_ids.discard(instance_id)
        selected_instance_ids.add(replacement_id)
        updated_rows[index] = replacement

    if unresolved_bad_ids:
        unresolved_text = ', '.join(sorted(unresolved_bad_ids))
        raise SystemExit(f'failed to find replacements for instance_ids: {unresolved_text}')
    return updated_rows


def _replace_group_track(
    benchmark_rows: list[dict[str, Any]],
    full_rows: list[dict[str, Any]],
    bad_ids: set[str],
    selection_field: str,
) -> list[dict[str, Any]]:
    full_groups_by_selection: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    for row in full_rows:
        selection_value = str(row.get(selection_field) or '')
        group_id = str(row.get('order_group_instance_id') or '')
        if selection_value and group_id:
            full_groups_by_selection[selection_value][group_id].append(row)

    benchmark_groups: list[list[dict[str, Any]]] = []
    group_index_by_instance_id: dict[str, int] = {}
    grouped_benchmark_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in benchmark_rows:
        group_id = str(row.get('order_group_instance_id') or '')
        if group_id:
            grouped_benchmark_rows[group_id].append(row)
    for rows in grouped_benchmark_rows.values():
        normalized = _normalize_group_rows(rows)
        if normalized is None:
            raise SystemExit('benchmark order_sensitivity track contains an incomplete group')
        benchmark_groups.append(normalized)
    benchmark_groups.sort(key=_group_sort_key)
    for group_index, group_rows in enumerate(benchmark_groups):
        for row in group_rows:
            instance_id = str(row.get('instance_id') or '').strip()
            if instance_id:
                group_index_by_instance_id[instance_id] = group_index

    selected_group_ids = {
        str(group_rows[0].get('order_group_instance_id') or '')
        for group_rows in benchmark_groups
        if group_rows
    }

    bad_group_indices = sorted(
        {
            group_index_by_instance_id[instance_id]
            for instance_id in bad_ids
            if instance_id in group_index_by_instance_id
        }
    )
    missing_bad_ids = sorted(instance_id for instance_id in bad_ids if instance_id not in group_index_by_instance_id)
    if missing_bad_ids:
        missing_text = ', '.join(missing_bad_ids)
        raise SystemExit(f'instance_ids not found in current benchmark track: {missing_text}')

    updated_groups = list(benchmark_groups)
    unresolved_group_ids: list[str] = []
    for group_index in bad_group_indices:
        current_group = benchmark_groups[group_index]
        selection_value = str(current_group[0].get(selection_field) or '')
        current_group_id = str(current_group[0].get('order_group_instance_id') or '')
        current_key = _group_sort_key(current_group)
        normalized_candidates = []
        for rows in full_groups_by_selection.get(selection_value, {}).values():
            normalized = _normalize_group_rows(rows)
            if normalized is not None:
                normalized_candidates.append(normalized)
        normalized_candidates.sort(key=_group_sort_key)
        later = []
        earlier = []
        for candidate_group in normalized_candidates:
            candidate_group_id = str(candidate_group[0].get('order_group_instance_id') or '')
            candidate_instance_ids = {
                str(row.get('instance_id') or '').strip()
                for row in candidate_group
                if str(row.get('instance_id') or '').strip()
            }
            if (
                not candidate_group_id
                or candidate_group_id == current_group_id
                or candidate_group_id in selected_group_ids
                or candidate_instance_ids.intersection(bad_ids)
            ):
                continue
            if _group_sort_key(candidate_group) > current_key:
                later.append(candidate_group)
            else:
                earlier.append(candidate_group)
        replacement_group = later[0] if later else (earlier[0] if earlier else None)
        if replacement_group is None:
            unresolved_group_ids.append(current_group_id)
            continue
        replacement_group_id = str(replacement_group[0].get('order_group_instance_id') or '')
        selected_group_ids.discard(current_group_id)
        selected_group_ids.add(replacement_group_id)
        updated_groups[group_index] = replacement_group

    if unresolved_group_ids:
        unresolved_text = ', '.join(sorted(unresolved_group_ids))
        raise SystemExit(f'failed to find replacement groups for order_group_instance_ids: {unresolved_text}')

    return [row for group_rows in updated_groups for row in group_rows]


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Refresh an engineering benchmark track by replacing compliance-failed samples with later in-track candidates.'
    )
    parser.add_argument('--track', required=True, choices=sorted(TRACK_CONFIGS))
    parser.add_argument('--benchmark-dir', default='data/benchmark')
    parser.add_argument('--source-dir', default='data/benchmark_full')
    parser.add_argument('--output-dir', default=None)
    parser.add_argument('--bad-instance-id', action='append', default=[])
    parser.add_argument('--bad-instance-ids-file', default=None)
    parser.add_argument('--predictions-path', default=None)
    args = parser.parse_args()

    track_cfg = TRACK_CONFIGS[args.track]
    benchmark_root = Path(args.benchmark_dir).resolve()
    source_root = Path(args.source_dir).resolve()
    benchmark_track_dir = benchmark_root / args.track
    source_track_dir = source_root / args.track
    output_dir = Path(args.output_dir).resolve() if args.output_dir else benchmark_track_dir
    bad_ids_file = Path(args.bad_instance_ids_file).resolve() if args.bad_instance_ids_file else None
    predictions_path = Path(args.predictions_path).resolve() if args.predictions_path else None

    benchmark_path = _resolve_file(benchmark_track_dir, track_cfg['data_file'])
    source_path = _resolve_file(source_track_dir, track_cfg['data_file'])
    summary_path = _resolve_optional_file(benchmark_track_dir, track_cfg['summary_file'])
    manifest_path = _resolve_optional_file(benchmark_track_dir, track_cfg['manifest_file'])

    bad_ids = _load_bad_instance_ids(
        manual_ids=list(args.bad_instance_id),
        ids_file=bad_ids_file,
        predictions_path=predictions_path,
    )
    if not bad_ids:
        raise SystemExit('no bad instance ids found; pass --bad-instance-id, --bad-instance-ids-file, or --predictions-path')

    benchmark_rows = _read_jsonl(benchmark_path)
    full_rows = _read_jsonl(source_path)
    if track_cfg['mode'] == 'row':
        updated_rows = _replace_row_track(
            benchmark_rows=benchmark_rows,
            full_rows=full_rows,
            bad_ids=bad_ids,
            selection_field=str(track_cfg['selection_field']),
        )
    else:
        updated_rows = _replace_group_track(
            benchmark_rows=benchmark_rows,
            full_rows=full_rows,
            bad_ids=bad_ids,
            selection_field=str(track_cfg['selection_field']),
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    _write_jsonl(output_dir / track_cfg['data_file'], updated_rows)
    if summary_path is not None:
        _write_csv(output_dir / track_cfg['summary_file'], _read_csv(summary_path))
    if manifest_path is not None:
        _write_csv(output_dir / track_cfg['manifest_file'], _read_csv(manifest_path))

    print(
        f'refreshed engineering subset: track={args.track} replaced_bad_ids={len(bad_ids)} '
        f'-> {output_dir / track_cfg["data_file"]}',
        flush=True,
    )


if __name__ == '__main__':
    main()
