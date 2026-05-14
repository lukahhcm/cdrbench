#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import statistics
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
    'difficulty_score',
    'difficulty_label',
    'difficulty_grid_cell',
    'recipe_difficulty_score',
    'recipe_difficulty_label',
    'operator_difficulty_sum',
    'operator_difficulty_mean',
    'recipe_length',
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


def _safe_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _load_atomic_operator_scores(path: str | None) -> dict[str, float]:
    if not path:
        return {}
    score_path = Path(path).resolve()
    if not score_path.exists():
        raise SystemExit(f'missing atomic operator score file: {score_path}')

    rows: list[dict[str, Any]]
    if score_path.suffix.lower() == '.json':
        payload = json.loads(score_path.read_text(encoding='utf-8'))
        rows = payload if isinstance(payload, list) else payload.get('by_operator', []) if isinstance(payload, dict) else []
    else:
        with score_path.open('r', encoding='utf-8', newline='') as handle:
            rows = list(csv.DictReader(handle))

    scores: dict[str, float] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        operator = str(row.get('operator') or row.get('operator_name') or row.get('op') or '').strip()
        if not operator:
            continue
        value = None
        for field in ('mean_rs', 'recipe_success_rate', 'rs', 'RS', 'mean_rs@k', 'RS@K', 'RS@3'):
            value = _safe_float(row.get(field))
            if value is not None:
                break
        if value is None:
            continue
        if 1.0 < value <= 100.0:
            value /= 100.0
        scores[operator] = max(0.0, min(1.0, value))
    return scores


def _sequence(row: dict[str, Any]) -> list[str]:
    sequence = row.get('operator_sequence')
    if isinstance(sequence, list):
        return [str(item) for item in sequence if str(item).strip()]
    operator = str(row.get('operator') or '').strip()
    return [operator] if operator else []


def _input_length_tier(row: dict[str, Any]) -> str:
    bucket = str(row.get('input_length_bucket') or '').strip().lower()
    if bucket in {'short', 'medium', 'long'}:
        return bucket
    length = int(row.get('input_length_chars', 0) or 0)
    if length <= 4_000:
        return 'short'
    if length <= 8_000:
        return 'medium'
    return 'long'


def _tertile_label(score: float, low_cut: float, high_cut: float) -> str:
    if score <= low_cut:
        return 'easy'
    if score <= high_cut:
        return 'medium'
    return 'hard'


def _task_difficulty_from_grid(recipe_label: str, input_label: str) -> str:
    recipe_rank = {'easy': 1, 'medium': 2, 'hard': 3}.get(recipe_label, 2)
    input_rank = {'short': 1, 'medium': 2, 'long': 3}.get(input_label, 2)
    grid_rank = recipe_rank + input_rank
    if grid_rank <= 3:
        return 'easy'
    if grid_rank <= 5:
        return 'medium'
    return 'hard'


def _attach_difficulty(
    rows: list[dict[str, Any]],
    *,
    atomic_operator_scores: dict[str, float],
    default_atomic_rs: float,
) -> list[dict[str, Any]]:
    scored_rows = []
    for row in rows:
        sequence = _sequence(row)
        op_difficulties = [
            1.0 - atomic_operator_scores.get(operator, default_atomic_rs)
            for operator in sequence
        ]
        op_sum = sum(op_difficulties)
        op_mean = op_sum / len(op_difficulties) if op_difficulties else 0.0
        copied = dict(row)
        copied['recipe_length'] = len(sequence)
        copied['operator_difficulty_sum'] = round(op_sum, 6)
        copied['operator_difficulty_mean'] = round(op_mean, 6)
        copied['recipe_difficulty_score'] = round(op_sum, 6)
        scored_rows.append(copied)

    scores = sorted(float(row.get('recipe_difficulty_score', 0.0) or 0.0) for row in scored_rows)
    if not scores:
        return scored_rows
    low_cut = scores[int((len(scores) - 1) / 3)]
    high_cut = scores[int(2 * (len(scores) - 1) / 3)]
    for row in scored_rows:
        recipe_score = float(row.get('recipe_difficulty_score', 0.0) or 0.0)
        recipe_label = _tertile_label(recipe_score, low_cut, high_cut)
        input_label = _input_length_tier(row)
        task_label = _task_difficulty_from_grid(recipe_label, input_label)
        row['recipe_difficulty_label'] = recipe_label
        row['input_length_bucket'] = input_label
        row['difficulty_grid_cell'] = f'recipe_{recipe_label}__input_{input_label}'
        row['difficulty_label'] = task_label
        row['difficulty_score'] = {'easy': 1, 'medium': 2, 'hard': 3}[task_label]
    return scored_rows


def _count_rows(rows: list[dict[str, Any]], fields: list[str]) -> list[dict[str, Any]]:
    counts: dict[tuple[str, ...], int] = {}
    for row in rows:
        key = tuple(str(row.get(field) or 'UNKNOWN') for field in fields)
        counts[key] = counts.get(key, 0) + 1
    output = []
    total = len(rows)
    for key, count in sorted(counts.items()):
        item = {field: value for field, value in zip(fields, key)}
        item['count'] = count
        item['fraction'] = count / total if total else 0.0
        output.append(item)
    return output


def _length_bucket(length: int) -> str:
    if length <= 1:
        return '1'
    if length == 2:
        return '2'
    if length == 3:
        return '3'
    if length == 4:
        return '4'
    return '5+'


def _recipe_distribution_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output = []
    by_recipe: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        recipe_key = str(row.get('recipe_variant_id') or row.get('recipe_id') or row.get('operator') or 'UNKNOWN')
        by_recipe.setdefault(recipe_key, []).append(row)
    for recipe_key, bucket in sorted(by_recipe.items()):
        first = bucket[0]
        lengths = [int(row.get('recipe_length', len(_sequence(row))) or 0) for row in bucket]
        scores = [float(row.get('difficulty_score', 0.0) or 0.0) for row in bucket]
        output.append(
            {
                'recipe_key': recipe_key,
                'benchmark_track': first.get('benchmark_track'),
                'domain': first.get('domain'),
                'recipe_id': first.get('recipe_id'),
                'recipe_variant_id': first.get('recipe_variant_id'),
                'order_family_id': first.get('order_family_id'),
                'count': len(bucket),
                'recipe_length': int(statistics.median(lengths)) if lengths else 0,
                'recipe_length_bucket': _length_bucket(int(statistics.median(lengths)) if lengths else 0),
                'mean_difficulty_score': sum(scores) / len(scores) if scores else 0.0,
            }
        )
    return output


def _prompt_distribution_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[int]] = {}
    for row in rows:
        variants = row.get('prompt_variants')
        if not isinstance(variants, list):
            continue
        for variant in variants:
            if not isinstance(variant, dict):
                continue
            style_id = str(variant.get('style_id') or 'UNKNOWN')
            style_label = str(variant.get('style_label') or style_id)
            instruction = str(variant.get('user_requirement') or '')
            grouped.setdefault((style_id, style_label), []).append(len(instruction))
    output = []
    for (style_id, style_label), lengths in sorted(grouped.items()):
        output.append(
            {
                'style_id': style_id,
                'style_label': style_label,
                'count': len(lengths),
                'mean_instruction_length_chars': sum(lengths) / len(lengths) if lengths else 0.0,
                'median_instruction_length_chars': statistics.median(lengths) if lengths else 0.0,
                'min_instruction_length_chars': min(lengths) if lengths else 0,
                'max_instruction_length_chars': max(lengths) if lengths else 0,
            }
        )
    return output


def _write_release_statistics(output_dir: Path, track: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    stats_dir = output_dir / 'stats'
    task_track_rows = _count_rows(rows, ['benchmark_track'])
    task_difficulty_rows = _count_rows(rows, ['difficulty_label'])
    task_difficulty_grid_rows = _count_rows(rows, ['recipe_difficulty_label', 'input_length_bucket', 'difficulty_label'])
    task_domain_rows = _count_rows(rows, ['domain'])
    task_domain_difficulty_rows = _count_rows(rows, ['domain', 'difficulty_label'])
    recipe_difficulty_rows = _count_rows(rows, ['recipe_difficulty_label'])
    recipe_length_rows = _count_rows(
        [{**row, 'recipe_length_bucket': _length_bucket(int(row.get('recipe_length', 0) or 0))} for row in rows],
        ['recipe_length_bucket'],
    )
    recipe_family_rows = _count_rows(rows, ['order_family_id']) if track == 'order_sensitivity' else _count_rows(rows, ['recipe_id'])
    prompt_variant_count_rows = _count_rows(rows, ['prompt_variant_count'])
    prompt_style_rows = _prompt_distribution_rows(rows)
    recipe_rows = _recipe_distribution_rows(rows)

    _write_csv(stats_dir / f'{track}_task_track_distribution.csv', task_track_rows)
    _write_csv(stats_dir / f'{track}_task_difficulty_distribution.csv', task_difficulty_rows)
    _write_csv(stats_dir / f'{track}_task_difficulty_grid_distribution.csv', task_difficulty_grid_rows)
    _write_csv(stats_dir / f'{track}_task_domain_distribution.csv', task_domain_rows)
    _write_csv(stats_dir / f'{track}_task_domain_by_difficulty.csv', task_domain_difficulty_rows)
    _write_csv(stats_dir / f'{track}_recipe_difficulty_distribution.csv', recipe_difficulty_rows)
    _write_csv(stats_dir / f'{track}_recipe_length_distribution.csv', recipe_length_rows)
    _write_csv(stats_dir / f'{track}_recipe_group_distribution.csv', recipe_family_rows)
    _write_csv(stats_dir / f'{track}_recipe_distribution.csv', recipe_rows)
    _write_csv(stats_dir / f'{track}_prompt_variant_count_distribution.csv', prompt_variant_count_rows)
    _write_csv(stats_dir / f'{track}_prompt_style_distribution.csv', prompt_style_rows)

    return {
        'task': {
            'track_distribution': task_track_rows,
            'difficulty_distribution': task_difficulty_rows,
            'difficulty_grid_distribution': task_difficulty_grid_rows,
            'domain_distribution': task_domain_rows,
            'domain_by_difficulty': task_domain_difficulty_rows,
        },
        'recipe': {
            'difficulty_distribution': recipe_difficulty_rows,
            'length_distribution': recipe_length_rows,
            'group_distribution': recipe_family_rows,
            'recipe_distribution_count': len(recipe_rows),
        },
        'prompt': {
            'prompt_variant_count_distribution': prompt_variant_count_rows,
            'style_distribution_count': len(prompt_style_rows),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Build a release-friendly benchmark copy without replaying Data-Juicer operators.'
    )
    parser.add_argument('--benchmark-root', default='data/benchmark')
    parser.add_argument('--output-root', default='data/benchmark_release')
    parser.add_argument('--tracks', default='atomic_ops,main,order_sensitivity')
    parser.add_argument('--keep-replay', action='store_true', help='Preserve recipe_replay if present in the input rows.')
    parser.add_argument(
        '--atomic-operator-score-path',
        default=None,
        help=(
            'Optional CSV/JSON file with per-operator atomic RS. Difficulty uses '
            'sum(1 - atomic_operator_rs) over the recipe. Missing operators use '
            '--default-atomic-rs.'
        ),
    )
    parser.add_argument(
        '--default-atomic-rs',
        type=float,
        default=0.5,
        help='Fallback atomic RS for operators absent from --atomic-operator-score-path.',
    )
    parser.add_argument('--progress-every', type=int, default=1000)
    args = parser.parse_args()

    benchmark_root = (ROOT / args.benchmark_root).resolve()
    output_root = (ROOT / args.output_root).resolve()
    track_names = [item.strip() for item in str(args.tracks).split(',') if item.strip()]
    unsupported = [track for track in track_names if track not in TRACK_FILENAMES]
    if unsupported:
        raise SystemExit(f'unsupported tracks: {", ".join(unsupported)}')

    default_atomic_rs = max(0.0, min(1.0, float(args.default_atomic_rs)))
    atomic_operator_scores = _load_atomic_operator_scores(args.atomic_operator_score_path)

    summary: dict[str, Any] = {
        'benchmark_root': str(benchmark_root),
        'output_root': str(output_root),
        'domain_metadata': DOMAIN_METADATA,
        'difficulty_definition': {
            'formula': (
                'recipe_difficulty_score = operator_difficulty_sum = '
                'sum(1 - atomic_operator_rs) over recipe operators. '
                'recipe_difficulty_label is assigned by tertiles within each output split. '
                'task difficulty is assigned by a 3x3 grid over recipe_difficulty_label '
                'and input_length_bucket.'
            ),
            'task_difficulty_grid': {
                'easy': ['recipe_easy__input_short', 'recipe_easy__input_medium', 'recipe_medium__input_short'],
                'medium': ['recipe_easy__input_long', 'recipe_medium__input_medium', 'recipe_hard__input_short'],
                'hard': ['recipe_medium__input_long', 'recipe_hard__input_medium', 'recipe_hard__input_long'],
            },
            'recipe_labeling': 'easy/medium/hard are recipe-difficulty tertiles within each output split.',
            'atomic_operator_score_path': str(Path(args.atomic_operator_score_path).resolve())
            if args.atomic_operator_score_path
            else None,
            'num_atomic_operator_scores': len(atomic_operator_scores),
            'default_atomic_rs': default_atomic_rs,
        },
        'tracks': {},
    }

    all_output_rows: list[dict[str, Any]] = []

    for track in track_names:
        input_path = _resolve_track_path(benchmark_root, track)
        rows = _read_jsonl(input_path)
        domain_counts: dict[str, int] = {}
        release_rows = []
        total_rows = len(rows)
        print(f'start release build track={track} rows={total_rows}', flush=True)
        for index, row in enumerate(rows, start=1):
            output_row = _ordered_row(row, keep_replay=bool(args.keep_replay))
            release_rows.append(output_row)
            if args.progress_every > 0 and (index % args.progress_every == 0 or index == total_rows):
                print(f'progress release build track={track} row={index}/{total_rows}', flush=True)

        scored_rows = _attach_difficulty(
            release_rows,
            atomic_operator_scores=atomic_operator_scores,
            default_atomic_rs=default_atomic_rs,
        )
        output_rows = [_ordered_row(row, keep_replay=bool(args.keep_replay)) for row in scored_rows]
        for output_row in output_rows:
            domain = str(output_row.get('domain') or 'unknown')
            domain_counts[domain] = domain_counts.get(domain, 0) + 1

        relative_parent = input_path.parent.relative_to(benchmark_root) if input_path.parent != benchmark_root else Path()
        output_path = output_root / relative_parent / input_path.name
        count = _write_jsonl(output_path, output_rows)
        stats_summary = _write_release_statistics(output_root, track, output_rows)
        all_output_rows.extend(output_rows)
        summary['tracks'][track] = {
            'input_path': str(input_path),
            'output_path': str(output_path),
            'rows': count,
            'domain_counts': dict(sorted(domain_counts.items())),
            'statistics': stats_summary,
        }
        print(f'wrote release track={track}: rows={count} -> {output_path}', flush=True)

    if all_output_rows:
        summary['all_tracks_statistics'] = _write_release_statistics(output_root, 'all', all_output_rows)

    _write_json(output_root / 'benchmark_release_summary.json', summary)
    print(f'wrote summary -> {output_root / "benchmark_release_summary.json"}', flush=True)


if __name__ == '__main__':
    main()
