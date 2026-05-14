#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[3]

TRACK_FILENAMES = {
    'atomic_ops': 'atomic_ops.jsonl',
    'main': 'main.jsonl',
    'order_sensitivity': 'order_sensitivity.jsonl',
}

DOMAIN_METADATA = {
    'web': {'domain_label': 'Web Refinement', 'domain_abbr': 'WR'},
    'arxiv': {'domain_label': 'LaTeX Refinement', 'domain_abbr': 'LR'},
    'knowledge_base': {'domain_label': 'RAG Preparation', 'domain_abbr': 'RP'},
    'pii': {'domain_label': 'Privacy Redaction', 'domain_abbr': 'PR'},
}

RELEASE_FIELD_ORDER = [
    'instance_id',
    'benchmark_track',
    'domain',
    'domain_label',
    'domain_abbr',
    'source_domain',
    'source_record_id',
    'input_text',
    'input_length_chars',
    'input_length_bucket',
    'operator',
    'operator_kind',
    'operator_sequence',
    'filter_name',
    'filter_params_by_name',
    'recipe_id',
    'recipe_variant_id',
    'recipe_type',
    'order_family_id',
    'order_slot',
    'order_group_instance_id',
    'group_success_rule',
    'reference_status',
    'reference_text',
    'reference_text_at_stop',
    'reference_text_full_run',
    'reference_trace',
    'recipe_prompt_key',
    'prompt_source',
    'prompt_variants',
    'prompt_variant_count',
    'prompt_candidate_pool_count',
    'prompt_sampling_policy',
    'prompt_sampling_seed',
    'accepted_candidate_count',
    'accepted_style_count',
    'threshold_meta',
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
            handle.write(json.dumps(row, ensure_ascii=False) + '\n')
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


def _resolve_track_path(root: Path, track: str) -> Path:
    filename = TRACK_FILENAMES[track]
    nested = root / track / filename
    if nested.exists():
        return nested
    flat = root / filename
    if flat.exists():
        return flat
    raise SystemExit(f'missing benchmark file for track={track}: expected {nested} or {flat}')


def _canonical_domain(row: dict[str, Any]) -> str:
    domain = str(row.get('domain') or '').strip()
    if domain in DOMAIN_METADATA:
        return domain
    source_domain = str(row.get('source_domain') or '').strip()
    if source_domain in DOMAIN_METADATA:
        return source_domain
    recipe_id = str(row.get('recipe_id') or row.get('recipe_variant_id') or '').strip()
    for candidate in DOMAIN_METADATA:
        if recipe_id.startswith(candidate + '_'):
            return candidate
    return domain or source_domain or 'unknown'


def _ordered_row(row: dict[str, Any], *, keep_replay: bool) -> dict[str, Any]:
    release_row = dict(row)
    domain = _canonical_domain(release_row)
    release_row['domain'] = domain
    if domain in DOMAIN_METADATA:
        release_row.update(DOMAIN_METADATA[domain])
    else:
        release_row.setdefault('domain_label', domain.replace('_', ' ').title())
        release_row.setdefault('domain_abbr', domain.upper())
    if not keep_replay:
        release_row.pop('recipe_replay', None)

    ordered = {key: release_row[key] for key in RELEASE_FIELD_ORDER if key in release_row}
    for key, value in release_row.items():
        if key not in ordered:
            ordered[key] = value
    return ordered


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Build a release-friendly benchmark copy without replaying Data-Juicer operators.'
    )
    parser.add_argument('--benchmark-root', default='data/benchmark')
    parser.add_argument('--output-root', default='data/benchmark_release')
    parser.add_argument('--tracks', default='atomic_ops,main,order_sensitivity')
    parser.add_argument('--keep-replay', action='store_true', help='Preserve recipe_replay if present in the input rows.')
    parser.add_argument('--progress-every', type=int, default=1000)
    args = parser.parse_args()

    benchmark_root = (ROOT / args.benchmark_root).resolve()
    output_root = (ROOT / args.output_root).resolve()
    track_names = [item.strip() for item in str(args.tracks).split(',') if item.strip()]
    unsupported = [track for track in track_names if track not in TRACK_FILENAMES]
    if unsupported:
        raise SystemExit(f'unsupported tracks: {", ".join(unsupported)}')

    summary: dict[str, Any] = {
        'benchmark_root': str(benchmark_root),
        'output_root': str(output_root),
        'domain_metadata': DOMAIN_METADATA,
        'tracks': {},
    }

    for track in track_names:
        input_path = _resolve_track_path(benchmark_root, track)
        rows = _read_jsonl(input_path)
        domain_counts: dict[str, int] = {}
        output_rows = []
        total_rows = len(rows)
        print(f'start release build track={track} rows={total_rows}', flush=True)
        for index, row in enumerate(rows, start=1):
            output_row = _ordered_row(row, keep_replay=bool(args.keep_replay))
            domain = str(output_row.get('domain') or 'unknown')
            domain_counts[domain] = domain_counts.get(domain, 0) + 1
            output_rows.append(output_row)
            if args.progress_every > 0 and (index % args.progress_every == 0 or index == total_rows):
                print(f'progress release build track={track} row={index}/{total_rows}', flush=True)

        relative_parent = input_path.parent.relative_to(benchmark_root) if input_path.parent != benchmark_root else Path()
        output_path = output_root / relative_parent / input_path.name
        count = _write_jsonl(output_path, output_rows)
        summary['tracks'][track] = {
            'input_path': str(input_path),
            'output_path': str(output_path),
            'rows': count,
            'domain_counts': dict(sorted(domain_counts.items())),
        }
        print(f'wrote release track={track}: rows={count} -> {output_path}', flush=True)

    _write_json(output_root / 'benchmark_release_summary.json', summary)
    print(f'wrote summary -> {output_root / "benchmark_release_summary.json"}', flush=True)


if __name__ == '__main__':
    main()
