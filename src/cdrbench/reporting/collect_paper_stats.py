#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Iterable

import pandas as pd
import yaml


ROOT = Path(__file__).resolve().parents[3]

TRACK_FILES = {
    "main": "main.jsonl",
    "order_sensitivity": "order_sensitivity.jsonl",
    "atomic_ops": "atomic_ops.jsonl",
}


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def _write_csv(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(list(rows)).to_csv(path, index=False)


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except Exception:
        return pd.DataFrame()


def _read_json(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _read_yaml(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _track_jsonl_path(benchmark_dir: Path, track: str) -> Path:
    direct = benchmark_dir / TRACK_FILES[track]
    nested = benchmark_dir / track / TRACK_FILES[track]
    return direct if direct.exists() else nested


def _track_csv_path(benchmark_dir: Path, track: str, filename: str) -> Path:
    direct = benchmark_dir / filename
    nested = benchmark_dir / track / filename
    return direct if direct.exists() else nested


def _safe_counter_records(counter: Counter[str], key_name: str) -> list[dict[str, Any]]:
    return [{key_name: key, "count": int(value)} for key, value in sorted(counter.items(), key=lambda item: (-item[1], item[0]))]


def _payload_type_name(payload: Any) -> str:
    if payload is None:
        return "none"
    if isinstance(payload, dict):
        return "dict"
    if isinstance(payload, list):
        return "list"
    return type(payload).__name__


def _sample_keys_from_mapping_rows(rows: list[dict[str, Any]], *, limit: int = 30) -> list[str]:
    keys: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row.keys():
            key_str = str(key)
            if key_str not in seen:
                seen.add(key_str)
                keys.append(key_str)
                if len(keys) >= limit:
                    return keys
    return keys


def _sample_scalar(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, dict):
        return {str(key): _sample_scalar(val) for key, val in list(value.items())[:8]}
    if isinstance(value, list):
        return [_sample_scalar(item) for item in value[:8]]
    return str(value)


def _structured_file_summary(path: Path, root: Path) -> dict[str, Any]:
    relative_path = str(path.relative_to(root))
    payload: Any = None
    file_type = path.suffix.lower().lstrip(".")
    row_count: int | None = None
    columns: list[str] = []
    sample_keys: list[str] = []
    top_level_type = "unknown"
    sample_record: Any = None

    if path.suffix.lower() == ".csv":
        df = _read_csv(path)
        row_count = int(len(df.index)) if not df.empty else 0
        columns = [str(column) for column in df.columns]
        if not df.empty:
            sample_record = {str(key): _sample_scalar(value) for key, value in df.iloc[0].to_dict().items()}
        top_level_type = "dataframe"
    elif path.suffix.lower() == ".jsonl":
        rows = _read_jsonl(path)
        row_count = len(rows)
        if rows and isinstance(rows[0], dict):
            sample_keys = _sample_keys_from_mapping_rows(rows)
            sample_record = _sample_scalar(rows[0])
            top_level_type = "jsonl_dict_rows"
        elif rows:
            sample_record = _sample_scalar(rows[0])
            top_level_type = "jsonl_rows"
        else:
            top_level_type = "jsonl_rows"
    elif path.suffix.lower() == ".json":
        payload = _read_json(path)
        top_level_type = _payload_type_name(payload)
        if isinstance(payload, dict):
            sample_keys = [str(key) for key in list(payload.keys())[:30]]
            sample_record = _sample_scalar(dict(list(payload.items())[:8]))
        elif isinstance(payload, list):
            row_count = len(payload)
            if payload and isinstance(payload[0], dict):
                sample_keys = _sample_keys_from_mapping_rows([item for item in payload if isinstance(item, dict)])
            if payload:
                sample_record = _sample_scalar(payload[0])
    elif path.suffix.lower() in {".yaml", ".yml"}:
        payload = _read_yaml(path)
        top_level_type = _payload_type_name(payload)
        if isinstance(payload, dict):
            sample_keys = [str(key) for key in list(payload.keys())[:30]]
            sample_record = _sample_scalar(dict(list(payload.items())[:8]))
        elif isinstance(payload, list):
            row_count = len(payload)
            if payload and isinstance(payload[0], dict):
                sample_keys = _sample_keys_from_mapping_rows([item for item in payload if isinstance(item, dict)])
            if payload:
                sample_record = _sample_scalar(payload[0])

    return {
        "root_relative_path": relative_path,
        "file_name": path.name,
        "parent_dir": path.parent.name,
        "suffix": path.suffix.lower(),
        "file_type": file_type,
        "size_bytes": int(path.stat().st_size),
        "row_count": row_count,
        "columns": ",".join(columns),
        "sample_keys": ",".join(sample_keys),
        "top_level_type": top_level_type,
        "sample_record": json.dumps(sample_record, ensure_ascii=False, sort_keys=True) if sample_record is not None else "",
    }


def _inventory_root(root: Path) -> dict[str, Any]:
    if not root.exists():
        return {"available": False, "root": str(root)}

    all_files = sorted(path for path in root.rglob("*") if path.is_file())
    structured_suffixes = {".csv", ".jsonl", ".json", ".yaml", ".yml"}
    structured_files = [path for path in all_files if path.suffix.lower() in structured_suffixes]
    file_rows = []
    suffix_counter: Counter[str] = Counter()
    dir_counter: Counter[str] = Counter()
    structured_type_counter: Counter[str] = Counter()

    for path in all_files:
        suffix_counter[path.suffix.lower() or "[no_suffix]"] += 1
        dir_counter[str(path.parent.relative_to(root))] += 1

    for path in structured_files:
        summary = _structured_file_summary(path, root)
        file_rows.append(summary)
        structured_type_counter[str(summary["suffix"] or "[no_suffix]")] += 1

    largest_files = sorted(
        (
            {
                "root_relative_path": str(path.relative_to(root)),
                "size_bytes": int(path.stat().st_size),
            }
            for path in all_files
        ),
        key=lambda item: (-item["size_bytes"], item["root_relative_path"]),
    )[:50]

    return {
        "available": True,
        "root": str(root),
        "total_file_count": len(all_files),
        "structured_file_count": len(structured_files),
        "suffix_counts": _safe_counter_records(suffix_counter, "suffix"),
        "directory_file_counts": _safe_counter_records(dir_counter, "directory"),
        "structured_suffix_counts": _safe_counter_records(structured_type_counter, "suffix"),
        "largest_files": largest_files,
        "file_rows": file_rows,
    }


def _flatten_subset_vs_full_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for track, track_payload in sorted(payload.items()):
        rows.append(
            {
                "track": track,
                "section": "overview",
                "key": "__track__",
                "full_count": track_payload.get("full_row_count"),
                "subset_count": track_payload.get("subset_row_count"),
                "selection_rate": track_payload.get("row_selection_rate"),
                "full_identity_count": track_payload.get("full_identity_count"),
                "subset_identity_count": track_payload.get("subset_identity_count"),
                "identity_retention_rate": track_payload.get("identity_retention_rate"),
            }
        )
        for section_name in ("domain_distribution", "type_distribution", "workflow_step_distribution", "operator_distribution"):
            for item in track_payload.get(section_name, []):
                category_key = next((key for key in item.keys() if key not in {"full_count", "subset_count", "selection_rate"}), "key")
                rows.append(
                    {
                        "track": track,
                        "section": section_name,
                        "key": item.get(category_key),
                        "full_count": item.get("full_count"),
                        "subset_count": item.get("subset_count"),
                        "selection_rate": item.get("selection_rate"),
                        "full_identity_count": None,
                        "subset_identity_count": None,
                        "identity_retention_rate": None,
                    }
                )
    return rows


def _inventory_manifest_rows(root_name: str, inventory: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in inventory.get("file_rows", []):
        rows.append({"root_name": root_name, **item})
    return rows


def _inventory_directory_rows(root_name: str, inventory: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in inventory.get("directory_file_counts", []):
        rows.append({"root_name": root_name, **item})
    return rows


def _inventory_largest_file_rows(root_name: str, inventory: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in inventory.get("largest_files", []):
        rows.append({"root_name": root_name, **item})
    return rows


def _preferred_filter_name(row: dict[str, Any]) -> str | None:
    threshold_meta = row.get("threshold_meta")
    if isinstance(threshold_meta, dict):
        filter_name = threshold_meta.get("filter_name")
        if filter_name:
            return str(filter_name)
    params_by_name = row.get("filter_params_by_name")
    if isinstance(params_by_name, dict) and params_by_name:
        return str(next(iter(params_by_name)))
    return None


def _op_kind(op_name: str) -> str:
    return "filter" if op_name.endswith("_filter") else "mapper"


def _sequence_stats(sequence: list[str]) -> dict[str, Any]:
    mapper_count = sum(1 for op_name in sequence if _op_kind(str(op_name)) == "mapper")
    filter_count = len(sequence) - mapper_count
    return {
        "workflow_step_count": len(sequence),
        "mapper_step_count": mapper_count,
        "filter_step_count": filter_count,
        "has_filter": filter_count > 0,
    }


def _quantiles(values: list[float]) -> dict[str, float | None]:
    if not values:
        return {"mean": None, "median": None, "p90": None, "min": None, "max": None}
    series = pd.Series(values, dtype="float64")
    return {
        "mean": round(float(series.mean()), 4),
        "median": round(float(series.median()), 4),
        "p90": round(float(series.quantile(0.9)), 4),
        "min": round(float(series.min()), 4),
        "max": round(float(series.max()), 4),
    }


def _change_ratio(input_text: str, output_text: str) -> float:
    if not input_text and not output_text:
        return 0.0
    return round(1.0 - SequenceMatcher(a=input_text, b=output_text).ratio(), 6)


def _flatten_operator_counts(rows: list[dict[str, Any]]) -> Counter[str]:
    counter: Counter[str] = Counter()
    for row in rows:
        for op_name in row.get("operator_sequence") or []:
            counter[str(op_name)] += 1
    return counter


def _load_track_rows(benchmark_dir: Path) -> dict[str, list[dict[str, Any]]]:
    return {track: _read_jsonl(_track_jsonl_path(benchmark_dir, track)) for track in TRACK_FILES}


def _distribution_from_rows(rows: list[dict[str, Any]], key: str) -> Counter[str]:
    counter: Counter[str] = Counter()
    for row in rows:
        value = row.get(key)
        if value is None:
            continue
        counter[str(value)] += 1
    return counter


def _sequence_length_distribution(rows: list[dict[str, Any]]) -> Counter[str]:
    counter: Counter[str] = Counter()
    for row in rows:
        sequence = row.get("operator_sequence") or []
        counter[str(len(sequence))] += 1
    return counter


def _track_identity_values(track: str, rows: list[dict[str, Any]]) -> set[str]:
    if track == "main":
        return {str(row.get("recipe_variant_id")) for row in rows if row.get("recipe_variant_id") is not None}
    if track == "order_sensitivity":
        return {str(row.get("order_family_id")) for row in rows if row.get("order_family_id") is not None}
    if track == "atomic_ops":
        return {str(row.get("operator")) for row in rows if row.get("operator") is not None}
    return set()


def _compare_counter(
    subset_counter: Counter[str],
    full_counter: Counter[str],
    *,
    key_name: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for key in sorted(set(full_counter) | set(subset_counter)):
        full_count = int(full_counter.get(key, 0))
        subset_count = int(subset_counter.get(key, 0))
        rows.append(
            {
                key_name: key,
                "full_count": full_count,
                "subset_count": subset_count,
                "selection_rate": round(subset_count / full_count, 6) if full_count > 0 else None,
            }
        )
    rows.sort(key=lambda item: (-(item["full_count"] or 0), str(item[key_name])))
    return rows


def _first_existing(paths: list[Path]) -> Path | None:
    for path in paths:
        if path.exists():
            return path
    return None


def _frame_records(df: pd.DataFrame, key_name: str, value_name: str = "count") -> list[dict[str, Any]]:
    if df.empty:
        return []
    rows: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        payload: dict[str, Any] = {}
        for key, value in row.items():
            if pd.isna(value):
                payload[str(key)] = None
            elif isinstance(value, (int, float)):
                payload[str(key)] = float(value) if isinstance(value, float) else int(value)
            else:
                payload[str(key)] = str(value)
        rows.append(payload)
    return rows


def _domain_jsonl_counts(directory: Path) -> list[dict[str, Any]]:
    if not directory.exists():
        return []
    rows: list[dict[str, Any]] = []
    for path in sorted(directory.glob("*.jsonl")):
        line_count = 0
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    line_count += 1
        rows.append({"file": path.name, "row_count": line_count})
    return rows


def _nested_csv_row_counts(root: Path, pattern: str, id_field: str) -> list[dict[str, Any]]:
    if not root.exists():
        return []
    rows: list[dict[str, Any]] = []
    for path in sorted(root.glob(pattern)):
        df = _read_csv(path)
        rows.append(
            {
                id_field: path.parent.name,
                "path": str(path),
                "row_count": int(len(df.index)) if not df.empty else 0,
                "columns": ",".join(str(column) for column in df.columns),
            }
        )
    return rows


def _processed_summary(processed_root: Path) -> dict[str, Any]:
    if not processed_root.exists():
        return {"available": False}

    domain_tags_dir = processed_root / "domain_tags"
    domain_filtered_dir = processed_root / "domain_filtered"
    recipe_mining_dir = processed_root / "recipe_mining"
    recipe_library_dir = processed_root / "recipe_library"
    prompt_library_dir = processed_root / "prompt_library"

    domain_labeling_summary = _read_csv(processed_root / "domain_labeling_summary.csv")
    domain_operator_catalog = _read_csv(processed_root / "domain_operator_catalog.csv")
    recipe_mining_summary = _read_csv(recipe_mining_dir / "domain_recipe_mining_summary.csv")
    recipe_library_summary = _read_csv(
        _first_existing(
            [
                recipe_library_dir / "recipe_library_summary.csv",
                recipe_library_dir / "workflow_library_summary.csv",
            ]
        )
        or recipe_library_dir / "recipe_library_summary.csv"
    )

    tagging = {
        "domain_tag_file_counts": _domain_jsonl_counts(domain_tags_dir),
        "domain_filtered_file_counts": _domain_jsonl_counts(domain_filtered_dir),
        "domain_labeling_summary_rows": int(len(domain_labeling_summary.index)) if not domain_labeling_summary.empty else 0,
        "domain_labeling_summary_columns": [str(column) for column in domain_labeling_summary.columns],
        "domain_operator_catalog_rows": int(len(domain_operator_catalog.index)) if not domain_operator_catalog.empty else 0,
        "domain_operator_catalog_columns": [str(column) for column in domain_operator_catalog.columns],
    }

    mining = {
        "domain_recipe_mining_summary_rows": int(len(recipe_mining_summary.index)) if not recipe_mining_summary.empty else 0,
        "domain_recipe_mining_summary_columns": [str(column) for column in recipe_mining_summary.columns],
        "selected_recipe_row_counts": _nested_csv_row_counts(recipe_mining_dir, "*/selected_recipes.csv", "domain"),
        "recipe_family_row_counts": _nested_csv_row_counts(recipe_mining_dir, "*/recipe_families.csv", "domain"),
    }

    recipe_library = {
        "recipe_library_summary_rows": int(len(recipe_library_summary.index)) if not recipe_library_summary.empty else 0,
        "recipe_library_summary_columns": [str(column) for column in recipe_library_summary.columns],
        "recipe_variant_row_counts": _nested_csv_row_counts(recipe_library_dir, "*/recipe_variants.csv", "domain"),
        "order_family_row_counts": _nested_csv_row_counts(recipe_library_dir, "*/order_sensitivity_families.csv", "domain"),
        "checkpoint_filter_stat_row_counts": _nested_csv_row_counts(recipe_library_dir, "*/checkpoint_filter_stats.csv", "domain"),
        "filter_attachment_row_counts": _nested_csv_row_counts(recipe_library_dir, "*/filter_attachments.csv", "domain"),
    }

    prompt_summary = {
        "prompt_library_available": prompt_library_dir.exists(),
        "prompt_generation_summary_rows": len(_read_jsonl(prompt_library_dir / "prompt_generation_summary.jsonl")),
        "recipe_prompt_library_rows": len(_read_jsonl(prompt_library_dir / "recipe_prompt_library.jsonl")),
    }

    return {
        "available": True,
        "paths": {
            "processed_root": str(processed_root),
            "domain_tags_dir": str(domain_tags_dir),
            "domain_filtered_dir": str(domain_filtered_dir),
            "recipe_mining_dir": str(recipe_mining_dir),
            "recipe_library_dir": str(recipe_library_dir),
            "prompt_library_dir": str(prompt_library_dir),
        },
        "tagging": tagging,
        "recipe_mining": mining,
        "recipe_library": recipe_library,
        "prompt_library": prompt_summary,
        "tables": {
            "domain_labeling_summary": _frame_records(domain_labeling_summary, "domain"),
            "domain_operator_catalog": _frame_records(domain_operator_catalog, "operator"),
            "domain_recipe_mining_summary": _frame_records(recipe_mining_summary, "domain"),
            "recipe_library_summary": _frame_records(recipe_library_summary, "domain"),
        },
    }


def _subset_vs_full_summary(
    subset_tracks: dict[str, list[dict[str, Any]]],
    full_tracks: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for track in TRACK_FILES:
        subset_rows = subset_tracks.get(track, [])
        full_rows = full_tracks.get(track, [])
        subset_identities = _track_identity_values(track, subset_rows)
        full_identities = _track_identity_values(track, full_rows)

        if track == "atomic_ops":
            subset_domain_counter = _distribution_from_rows(subset_rows, "source_domain")
            full_domain_counter = _distribution_from_rows(full_rows, "source_domain")
            subset_type_counter = _distribution_from_rows(subset_rows, "operator_kind")
            full_type_counter = _distribution_from_rows(full_rows, "operator_kind")
        else:
            subset_domain_counter = _distribution_from_rows(subset_rows, "domain")
            full_domain_counter = _distribution_from_rows(full_rows, "domain")
            subset_type_counter = (
                _distribution_from_rows(subset_rows, "recipe_type")
                if track != "atomic_ops"
                else _distribution_from_rows(subset_rows, "operator_kind")
            )
            full_type_counter = (
                _distribution_from_rows(full_rows, "recipe_type")
                if track != "atomic_ops"
                else _distribution_from_rows(full_rows, "operator_kind")
            )

        summary[track] = {
            "full_row_count": len(full_rows),
            "subset_row_count": len(subset_rows),
            "row_selection_rate": round(len(subset_rows) / len(full_rows), 6) if full_rows else None,
            "full_identity_count": len(full_identities),
            "subset_identity_count": len(subset_identities),
            "identity_retention_rate": round(len(subset_identities) / len(full_identities), 6) if full_identities else None,
            "domain_distribution": _compare_counter(
                subset_domain_counter,
                full_domain_counter,
                key_name="domain" if track != "atomic_ops" else "source_domain",
            ),
            "type_distribution": _compare_counter(
                subset_type_counter,
                full_type_counter,
                key_name="recipe_type" if track != "atomic_ops" else "operator_kind",
            ),
            "workflow_step_distribution": _compare_counter(
                _sequence_length_distribution(subset_rows),
                _sequence_length_distribution(full_rows),
                key_name="workflow_step_count",
            ),
            "operator_distribution": _compare_counter(
                _flatten_operator_counts(subset_rows) if track != "atomic_ops" else _distribution_from_rows(subset_rows, "operator"),
                _flatten_operator_counts(full_rows) if track != "atomic_ops" else _distribution_from_rows(full_rows, "operator"),
                key_name="operator",
            ),
        }
    return summary


def _main_records(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    enriched: list[dict[str, Any]] = []
    domains: Counter[str] = Counter()
    recipe_types: Counter[str] = Counter()
    ref_status: Counter[str] = Counter()
    input_buckets: Counter[str] = Counter()
    step_counts: Counter[str] = Counter()
    mapper_step_counts: Counter[str] = Counter()
    filter_step_counts: Counter[str] = Counter()
    filter_names: Counter[str] = Counter()
    changed_keep = 0
    changed_any = 0
    change_ratios: list[float] = []
    input_lengths: list[float] = []

    for row in rows:
        sequence = [str(op_name) for op_name in (row.get("operator_sequence") or [])]
        seq_stats = _sequence_stats(sequence)
        input_text = str(row.get("input_text") or "")
        reference_text = str(row.get("reference_text") or "")
        change_ratio = _change_ratio(input_text, reference_text)
        filter_name = _preferred_filter_name(row)
        enriched_row = {
            "instance_id": row.get("instance_id"),
            "domain": str(row.get("domain") or "unknown"),
            "recipe_id": row.get("recipe_id"),
            "recipe_variant_id": row.get("recipe_variant_id"),
            "recipe_type": str(row.get("recipe_type") or "unknown"),
            "reference_status": str(row.get("reference_status") or "unknown"),
            "input_length_chars": int(row.get("input_length_chars") or 0),
            "input_length_bucket": str(row.get("input_length_bucket") or "unknown"),
            "workflow_step_count": seq_stats["workflow_step_count"],
            "mapper_step_count": seq_stats["mapper_step_count"],
            "filter_step_count": seq_stats["filter_step_count"],
            "has_filter": bool(seq_stats["has_filter"]),
            "filter_name": filter_name,
            "changed_from_input": bool(reference_text != input_text),
            "change_ratio": change_ratio,
        }
        enriched.append(enriched_row)

        domains[enriched_row["domain"]] += 1
        recipe_types[enriched_row["recipe_type"]] += 1
        ref_status[enriched_row["reference_status"]] += 1
        input_buckets[enriched_row["input_length_bucket"]] += 1
        step_counts[str(enriched_row["workflow_step_count"])] += 1
        mapper_step_counts[str(enriched_row["mapper_step_count"])] += 1
        filter_step_counts[str(enriched_row["filter_step_count"])] += 1
        if filter_name:
            filter_names[filter_name] += 1
        if reference_text != input_text:
            changed_any += 1
        if enriched_row["reference_status"] == "KEEP" and reference_text != input_text:
            changed_keep += 1
        change_ratios.append(change_ratio)
        input_lengths.append(float(enriched_row["input_length_chars"]))

    summary = {
        "row_count": len(rows),
        "unique_recipe_ids": len({str(row.get("recipe_id")) for row in rows if row.get("recipe_id") is not None}),
        "unique_recipe_variant_ids": len(
            {str(row.get("recipe_variant_id")) for row in rows if row.get("recipe_variant_id") is not None}
        ),
        "active_domains": sorted(domains),
        "domain_counts": _safe_counter_records(domains, "domain"),
        "recipe_type_counts": _safe_counter_records(recipe_types, "recipe_type"),
        "reference_status_counts": _safe_counter_records(ref_status, "reference_status"),
        "input_length_bucket_counts": _safe_counter_records(input_buckets, "input_length_bucket"),
        "workflow_step_count_distribution": _safe_counter_records(step_counts, "workflow_step_count"),
        "mapper_step_count_distribution": _safe_counter_records(mapper_step_counts, "mapper_step_count"),
        "filter_step_count_distribution": _safe_counter_records(filter_step_counts, "filter_step_count"),
        "filter_name_counts": _safe_counter_records(filter_names, "filter_name"),
        "input_length_stats": _quantiles(input_lengths),
        "change_ratio_stats": _quantiles(change_ratios),
        "changed_from_input_rate": round(changed_any / len(rows), 6) if rows else None,
        "changed_keep_rate": round(changed_keep / len(rows), 6) if rows else None,
    }
    return enriched, summary


def _order_records(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    enriched: list[dict[str, Any]] = []
    group_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    domain_groups: Counter[str] = Counter()
    slot_counts: Counter[str] = Counter()
    slot_status_counts: Counter[str] = Counter()
    group_signature_counts: Counter[str] = Counter()
    input_lengths: list[float] = []

    for row in rows:
        sequence = [str(op_name) for op_name in (row.get("operator_sequence") or [])]
        seq_stats = _sequence_stats(sequence)
        group_id = str(row.get("order_group_instance_id") or "")
        slot = str(row.get("order_slot") or "unknown")
        status = str(row.get("reference_status") or "unknown")
        enriched_row = {
            "instance_id": row.get("instance_id"),
            "order_group_instance_id": group_id,
            "order_family_id": row.get("order_family_id"),
            "domain": str(row.get("domain") or "unknown"),
            "recipe_id": row.get("recipe_id"),
            "recipe_variant_id": row.get("recipe_variant_id"),
            "recipe_type": str(row.get("recipe_type") or "unknown"),
            "order_slot": slot,
            "reference_status": status,
            "input_length_chars": int(row.get("input_length_chars") or 0),
            "input_length_bucket": str(row.get("input_length_bucket") or "unknown"),
            "workflow_step_count": seq_stats["workflow_step_count"],
            "mapper_step_count": seq_stats["mapper_step_count"],
            "filter_step_count": seq_stats["filter_step_count"],
            "filter_name": _preferred_filter_name(row),
        }
        enriched.append(enriched_row)
        group_rows[group_id].append(row)
        slot_counts[slot] += 1
        slot_status_counts[f"{slot}::{status}"] += 1
        input_lengths.append(float(enriched_row["input_length_chars"]))

    group_detail_rows: list[dict[str, Any]] = []
    for group_id, items in group_rows.items():
        signatures = {(str(item.get("reference_status") or "unknown"), str(item.get("reference_text") or "")) for item in items}
        signature_count = len(signatures)
        domain = str(items[0].get("domain") or "unknown") if items else "unknown"
        order_family_id = str(items[0].get("order_family_id") or "") if items else ""
        domain_groups[domain] += 1
        group_signature_counts[str(signature_count)] += 1
        group_detail_rows.append(
            {
                "order_group_instance_id": group_id,
                "order_family_id": order_family_id,
                "domain": domain,
                "slot_count": len(items),
                "distinct_reference_count": signature_count,
            }
        )

    summary = {
        "row_count": len(rows),
        "unique_order_family_ids": len({str(row.get("order_family_id")) for row in rows if row.get("order_family_id")}),
        "unique_order_group_ids": len(group_rows),
        "domain_group_counts": _safe_counter_records(domain_groups, "domain"),
        "slot_counts": _safe_counter_records(slot_counts, "order_slot"),
        "slot_status_counts": _safe_counter_records(slot_status_counts, "slot_status"),
        "group_signature_distribution": _safe_counter_records(group_signature_counts, "distinct_reference_count"),
        "input_length_stats": _quantiles(input_lengths),
    }
    return enriched + group_detail_rows, summary


def _atomic_records(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    enriched: list[dict[str, Any]] = []
    operators: Counter[str] = Counter()
    operator_kinds: Counter[str] = Counter()
    source_domains: Counter[str] = Counter()
    ref_status: Counter[str] = Counter()
    input_buckets: Counter[str] = Counter()
    input_lengths: list[float] = []

    for row in rows:
        operator = str(row.get("operator") or "unknown")
        operator_kind = str(row.get("operator_kind") or _op_kind(operator))
        source_domain = str(row.get("source_domain") or "unknown")
        input_bucket = str(row.get("input_length_bucket") or "unknown")
        ref_status_value = str(row.get("reference_status") or "unknown")
        enriched_row = {
            "instance_id": row.get("instance_id"),
            "operator": operator,
            "operator_kind": operator_kind,
            "source_domain": source_domain,
            "reference_status": ref_status_value,
            "input_length_chars": int(row.get("input_length_chars") or 0),
            "input_length_bucket": input_bucket,
        }
        enriched.append(enriched_row)
        operators[operator] += 1
        operator_kinds[operator_kind] += 1
        source_domains[source_domain] += 1
        ref_status[ref_status_value] += 1
        input_buckets[input_bucket] += 1
        input_lengths.append(float(enriched_row["input_length_chars"]))

    summary = {
        "row_count": len(rows),
        "unique_operators": len(operators),
        "unique_mapper_operators": len([name for name in operators if _op_kind(name) == "mapper"]),
        "unique_filter_operators": len([name for name in operators if _op_kind(name) == "filter"]),
        "operator_counts": _safe_counter_records(operators, "operator"),
        "operator_kind_counts": _safe_counter_records(operator_kinds, "operator_kind"),
        "source_domain_counts": _safe_counter_records(source_domains, "source_domain"),
        "reference_status_counts": _safe_counter_records(ref_status, "reference_status"),
        "input_length_bucket_counts": _safe_counter_records(input_buckets, "input_length_bucket"),
        "input_length_stats": _quantiles(input_lengths),
    }
    return enriched, summary


def _load_prompt_rows(prompt_dir: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    summary_rows = _read_jsonl(prompt_dir / "prompt_generation_summary.jsonl")
    library_rows = _read_jsonl(prompt_dir / "recipe_prompt_library.jsonl")
    return summary_rows, library_rows


def _prompt_summary(prompt_root: Path) -> dict[str, Any]:
    if not prompt_root.exists():
        return {"available": False}

    track_rows: dict[str, dict[str, Any]] = {}
    per_recipe_rows: list[dict[str, Any]] = []
    style_counter: Counter[str] = Counter()
    accepted_style_counter: Counter[str] = Counter()

    for track in TRACK_FILES:
        track_dir = prompt_root / track
        summary_rows, library_rows = _load_prompt_rows(track_dir)
        if summary_rows:
            track_rows[track] = summary_rows[0]
        for row in library_rows:
            candidates = row.get("candidates") or []
            accepted_style_ids = {str(candidate.get("style_id") or "unknown") for candidate in candidates}
            judged = row.get("judged_candidate_summary") or []
            for judged_item in judged:
                style_counter[str(judged_item.get("style_id") or "unknown")] += 1
                if judged_item.get("accepted"):
                    accepted_style_counter[str(judged_item.get("style_id") or "unknown")] += 1
            per_recipe_rows.append(
                {
                    "track": track,
                    "recipe_prompt_key": row.get("recipe_prompt_key"),
                    "domain": row.get("domain"),
                    "requested_style_count": int(row.get("requested_style_count") or 0),
                    "requested_candidate_count": int(row.get("requested_candidate_count") or 0),
                    "accepted_candidate_count": int(row.get("accepted_candidate_count") or 0),
                    "accepted_style_count": int(row.get("accepted_style_count") or 0),
                    "accepted_style_ids": ",".join(sorted(accepted_style_ids)),
                }
            )

    track_summaries = []
    for track, row in sorted(track_rows.items()):
        track_summaries.append(
            {
                "track": track,
                "recipe_count": int(row.get("recipe_count") or 0),
                "accepted_recipe_count": int(row.get("accepted_recipe_count") or 0),
                "generated_candidate_count": int(row.get("generated_candidate_count") or 0),
                "accepted_candidate_count": int(row.get("accepted_candidate_count") or 0),
                "variants_per_recipe": int(row.get("variants_per_recipe") or 0),
                "candidates_per_style": int(row.get("candidates_per_style") or 0),
            }
        )

    return {
        "available": bool(track_rows or per_recipe_rows),
        "track_summaries": track_summaries,
        "style_request_counts": _safe_counter_records(style_counter, "style_id"),
        "accepted_style_counts": _safe_counter_records(accepted_style_counter, "style_id"),
        "per_recipe_rows": per_recipe_rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect paper-oriented benchmark statistics and export raw summary tables.")
    parser.add_argument("--benchmark-dir", default="data/benchmark")
    parser.add_argument(
        "--benchmark-full-dir",
        default=None,
        help="Optional full benchmark directory used before subset selection. When provided, emit subset-vs-full retention stats.",
    )
    parser.add_argument("--prompt-root", default="data/benchmark_prompts")
    parser.add_argument(
        "--processed-root",
        default="data/processed",
        help="Processed intermediate outputs root. Used to summarize tagging, recipe mining, recipe library, and prompt-library construction artifacts.",
    )
    parser.add_argument("--output-dir", default="data/paper_stats/collected")
    args = parser.parse_args()

    benchmark_dir = (ROOT / args.benchmark_dir).resolve()
    benchmark_full_dir = (ROOT / args.benchmark_full_dir).resolve() if args.benchmark_full_dir else None
    prompt_root = (ROOT / args.prompt_root).resolve()
    processed_root = (ROOT / args.processed_root).resolve()
    output_dir = (ROOT / args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    track_rows = _load_track_rows(benchmark_dir)
    main_rows, main_summary = _main_records(track_rows["main"])
    order_rows, order_summary = _order_records(track_rows["order_sensitivity"])
    atomic_rows, atomic_summary = _atomic_records(track_rows["atomic_ops"])
    prompt_summary = _prompt_summary(prompt_root)
    processed_summary = _processed_summary(processed_root)
    benchmark_inventory = _inventory_root(benchmark_dir)
    benchmark_full_inventory = _inventory_root(benchmark_full_dir) if benchmark_full_dir is not None else {"available": False}
    processed_inventory = _inventory_root(processed_root)

    all_ops = set()
    for row in track_rows["main"] + track_rows["order_sensitivity"]:
        all_ops.update(str(op_name) for op_name in (row.get("operator_sequence") or []))
    all_ops.update(str(row.get("operator") or "unknown") for row in track_rows["atomic_ops"])
    all_domains = sorted(
        {
            *(str(row.get("domain") or "unknown") for row in track_rows["main"]),
            *(str(row.get("domain") or "unknown") for row in track_rows["order_sensitivity"]),
            *(str(row.get("source_domain") or "unknown") for row in track_rows["atomic_ops"]),
        }
    )

    overview = {
        "benchmark_dir": str(benchmark_dir),
        "benchmark_full_dir": str(benchmark_full_dir) if benchmark_full_dir else None,
        "processed_root": str(processed_root),
        "tracks": {
            "main": len(track_rows["main"]),
            "order_sensitivity": len(track_rows["order_sensitivity"]),
            "atomic_ops": len(track_rows["atomic_ops"]),
        },
        "total_instances": sum(len(rows) for rows in track_rows.values()),
        "active_domains": all_domains,
        "unique_operators_across_tracks": len([op_name for op_name in all_ops if op_name and op_name != "unknown"]),
        "unique_mapper_operators_across_tracks": len(
            [op_name for op_name in all_ops if op_name and op_name != "unknown" and _op_kind(op_name) == "mapper"]
        ),
        "unique_filter_operators_across_tracks": len(
            [op_name for op_name in all_ops if op_name and op_name != "unknown" and _op_kind(op_name) == "filter"]
        ),
        "main": main_summary,
        "order_sensitivity": order_summary,
        "atomic_ops": atomic_summary,
        "prompts": {key: value for key, value in prompt_summary.items() if key != "per_recipe_rows"},
        "processed": {key: value for key, value in processed_summary.items() if key != "tables"},
        "benchmark_inventory": {key: value for key, value in benchmark_inventory.items() if key != "file_rows"},
        "benchmark_full_inventory": {key: value for key, value in benchmark_full_inventory.items() if key != "file_rows"},
        "processed_inventory": {key: value for key, value in processed_inventory.items() if key != "file_rows"},
    }

    subset_vs_full = None
    if benchmark_full_dir is not None:
        full_track_rows = _load_track_rows(benchmark_full_dir)
        subset_vs_full = _subset_vs_full_summary(track_rows, full_track_rows)
        overview["subset_vs_full"] = subset_vs_full

    _write_json(output_dir / "summary.json", overview)
    _write_csv(output_dir / "main_instance_stats.csv", main_rows)
    _write_csv(output_dir / "main_operator_frequency.csv", _safe_counter_records(_flatten_operator_counts(track_rows["main"]), "operator"))
    _write_csv(output_dir / "order_stats.csv", order_rows)
    _write_csv(output_dir / "order_operator_frequency.csv", _safe_counter_records(_flatten_operator_counts(track_rows["order_sensitivity"]), "operator"))
    _write_csv(output_dir / "atomic_instance_stats.csv", atomic_rows)
    _write_csv(output_dir / "prompt_recipe_stats.csv", prompt_summary.get("per_recipe_rows") or [])
    _write_csv(
        output_dir / "benchmark_file_inventory.csv",
        _inventory_manifest_rows("benchmark", benchmark_inventory),
    )
    _write_csv(
        output_dir / "processed_file_inventory.csv",
        _inventory_manifest_rows("processed", processed_inventory),
    )
    if benchmark_full_dir is not None:
        _write_csv(
            output_dir / "benchmark_full_file_inventory.csv",
            _inventory_manifest_rows("benchmark_full", benchmark_full_inventory),
        )
    _write_csv(
        output_dir / "root_directory_counts.csv",
        [
            *_inventory_directory_rows("benchmark", benchmark_inventory),
            *_inventory_directory_rows("processed", processed_inventory),
            *(_inventory_directory_rows("benchmark_full", benchmark_full_inventory) if benchmark_full_dir is not None else []),
        ],
    )
    _write_csv(
        output_dir / "root_largest_files.csv",
        [
            *_inventory_largest_file_rows("benchmark", benchmark_inventory),
            *_inventory_largest_file_rows("processed", processed_inventory),
            *(_inventory_largest_file_rows("benchmark_full", benchmark_full_inventory) if benchmark_full_dir is not None else []),
        ],
    )
    _write_csv(
        output_dir / "processed_key_tables.csv",
        [
            *processed_summary.get("tables", {}).get("domain_labeling_summary", []),
            *processed_summary.get("tables", {}).get("domain_operator_catalog", []),
            *processed_summary.get("tables", {}).get("domain_recipe_mining_summary", []),
            *processed_summary.get("tables", {}).get("recipe_library_summary", []),
        ],
    )
    if subset_vs_full is not None:
        _write_csv(output_dir / "subset_vs_full.csv", _flatten_subset_vs_full_rows(subset_vs_full))

    print(f"wrote summary -> {output_dir / 'summary.json'}", flush=True)
    print(f"wrote main stats -> {output_dir / 'main_instance_stats.csv'}", flush=True)
    print(f"wrote order stats -> {output_dir / 'order_stats.csv'}", flush=True)
    print(f"wrote atomic stats -> {output_dir / 'atomic_instance_stats.csv'}", flush=True)
    print(f"wrote inventories -> {output_dir}", flush=True)
    if subset_vs_full is not None:
        print(f"wrote subset-vs-full stats -> {output_dir}", flush=True)


if __name__ == "__main__":
    main()
