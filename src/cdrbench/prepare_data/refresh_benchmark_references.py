#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml

from cdrbench.config import load_domains_config
from cdrbench.domain_assignment import build_domain_execution_plan
from cdrbench.prepare_data.materialize_benchmark_instances import (
    ROOT,
    _execute_recipe,
    _execute_recipe_without_early_stop,
    _operator_lookup,
)


TRACK_FILENAMES = {
    'atomic_ops': 'atomic_ops.jsonl',
    'main': 'main.jsonl',
    'order_sensitivity': 'order_sensitivity.jsonl',
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


def _resolve_track_path(root: Path, track: str) -> Path:
    filename = TRACK_FILENAMES[track]
    direct = root / track / filename
    if direct.exists():
        return direct
    fallback = root / filename
    if fallback.exists():
        return fallback
    raise SystemExit(f'missing benchmark file for track={track}: expected {direct} or {fallback}')


def _load_recipe_variant_index(recipe_library_dir: Path) -> dict[str, dict[str, Any]]:
    variant_index: dict[str, dict[str, Any]] = {}
    paths = sorted(recipe_library_dir.glob('*/recipe_library.yaml'))
    if not paths:
        paths = sorted(recipe_library_dir.glob('*/workflow_library.yaml'))
    for path in paths:
        with path.open('r', encoding='utf-8') as handle:
            payload = yaml.safe_load(handle) or {}
        recipes = payload.get('recipes') or payload.get('workflows') or []
        if not isinstance(recipes, list):
            continue
        for recipe in recipes:
            if not isinstance(recipe, dict):
                continue
            variants = [
                *(recipe.get('main_recipe_variants') or recipe.get('main_workflow_variants') or []),
                *(recipe.get('order_sensitivity_recipe_variants') or recipe.get('order_sensitivity_variants') or []),
            ]
            for variant in variants:
                if not isinstance(variant, dict):
                    continue
                variant_id = str(variant.get('recipe_variant_id') or variant.get('workflow_variant_id') or '').strip()
                if not variant_id:
                    continue
                variant_index[variant_id] = variant
    return variant_index


def _resolve_sequence_and_filter_params(
    row: dict[str, Any],
    recipe_variant_index: dict[str, dict[str, Any]],
) -> tuple[list[str], dict[str, dict[str, Any]], dict[str, Any] | None]:
    sequence = [str(item) for item in row.get('operator_sequence') or [] if str(item).strip()]
    filter_params_by_name = (
        dict(row.get('filter_params_by_name'))
        if isinstance(row.get('filter_params_by_name'), dict)
        else {}
    )
    if sequence:
        return sequence, filter_params_by_name, None

    variant_id = str(row.get('recipe_variant_id') or '').strip()
    variant = recipe_variant_index.get(variant_id)
    if variant is None:
        raise RuntimeError(
            f'missing operator_sequence and unable to resolve recipe_variant_id={variant_id or "<empty>"} from recipe library'
        )

    sequence = [str(item) for item in variant.get('operator_sequence') or [] if str(item).strip()]
    if not sequence:
        raise RuntimeError(f'recipe library variant {variant_id} has no operator_sequence')

    if not filter_params_by_name:
        filter_name = str(variant.get('filter_name') or '').strip()
        filter_params = variant.get('filter_params')
        if filter_name and isinstance(filter_params, dict):
            filter_params_by_name = {filter_name: dict(filter_params)}

    return sequence, filter_params_by_name, variant


def _refresh_row(
    row: dict[str, Any],
    operators_by_name: dict[str, dict[str, Any]],
    recipe_variant_index: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    sequence, filter_params_by_name, variant = _resolve_sequence_and_filter_params(row, recipe_variant_index)
    if not sequence:
        raise RuntimeError(f'missing operator_sequence for instance_id={row.get("instance_id")}')
    pseudo_record = {
        'text': str(row.get('input_text', '')),
        'source_name': row.get('source_name'),
        'url': row.get('url'),
    }
    execution = _execute_recipe(
        pseudo_record,
        sequence,
        operators_by_name,
        filter_params_by_name,
    )
    refreshed = dict(row)
    refreshed['operator_sequence'] = sequence
    refreshed['filter_params_by_name'] = filter_params_by_name
    if variant is not None:
        refreshed.setdefault('filter_name', variant.get('filter_name'))
        refreshed.setdefault('recipe_type', variant.get('recipe_type') or variant.get('workflow_type'))
        refreshed.setdefault('benchmark_track', variant.get('benchmark_track'))
        refreshed.setdefault('order_slot', variant.get('order_slot'))
        refreshed.setdefault('order_family_id', variant.get('order_family_id'))
    refreshed['reference_status'] = execution['reference_status']
    refreshed['reference_text'] = execution['reference_text']
    refreshed.pop('reference_text_at_drop', None)
    refreshed.pop('intermediate_text_at_drop', None)
    refreshed['reference_trace'] = execution['trace']

    if str(row.get('benchmark_track') or '') == 'order_sensitivity':
        full_run_execution = _execute_recipe_without_early_stop(
            pseudo_record,
            sequence,
            operators_by_name,
            filter_params_by_name,
        )
        refreshed['reference_text_full_run'] = full_run_execution.get('reference_text')
        refreshed.pop('full_run_reference_text', None)
        refreshed['full_run_reference_trace'] = full_run_execution.get('trace')

    return refreshed


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Refresh deterministic reference fields in existing benchmark JSONL files without rematerializing selection.'
    )
    parser.add_argument('--benchmark-root', default='data/benchmark_full')
    parser.add_argument('--output-root', default=None, help='Optional alternate output root; defaults to overwriting benchmark-root.')
    parser.add_argument('--tracks', default='atomic_ops,main,order_sensitivity')
    parser.add_argument('--domains-config', default='configs/domains.yaml')
    parser.add_argument('--recipe-library-dir', default='data/processed/recipe_library')
    args = parser.parse_args()

    benchmark_root = (ROOT / args.benchmark_root).resolve()
    output_root = benchmark_root if args.output_root is None else (ROOT / args.output_root).resolve()
    recipe_library_dir = (ROOT / args.recipe_library_dir).resolve()
    track_names = [item.strip() for item in str(args.tracks).split(',') if item.strip()]
    unsupported = [track for track in track_names if track not in TRACK_FILENAMES]
    if unsupported:
        raise SystemExit(f'unsupported tracks: {", ".join(unsupported)}')

    domains_cfg = load_domains_config(ROOT / args.domains_config)
    plan = build_domain_execution_plan(domains_cfg)
    operators_by_name = _operator_lookup(plan)
    recipe_variant_index = _load_recipe_variant_index(recipe_library_dir)

    for track in track_names:
        input_path = _resolve_track_path(benchmark_root, track)
        rows = _read_jsonl(input_path)
        refreshed_rows = []
        for index, row in enumerate(rows, start=1):
            try:
                refreshed_rows.append(_refresh_row(row, operators_by_name, recipe_variant_index))
            except Exception as exc:
                raise SystemExit(
                    f'failed to refresh track={track} instance_id={row.get("instance_id")} row_index={index}: {exc}'
                ) from exc
        relative_parent = input_path.parent.relative_to(benchmark_root) if input_path.parent != benchmark_root else Path()
        output_path = output_root / relative_parent / input_path.name
        _write_jsonl(output_path, refreshed_rows)
        print(f'refreshed {track}: rows={len(refreshed_rows)} -> {output_path}', flush=True)


if __name__ == '__main__':
    main()
