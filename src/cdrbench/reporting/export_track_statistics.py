#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

import pandas as pd


ROOT = Path(__file__).resolve().parents[3]

TRACK_FILES = {
    "main": "main.jsonl",
    "order_sensitivity": "order_sensitivity.jsonl",
    "atomic_ops": "atomic_ops.jsonl",
}


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
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


def _track_path(base_dir: Path, track: str) -> Path:
    direct = base_dir / TRACK_FILES[track]
    nested = base_dir / track / TRACK_FILES[track]
    if direct.exists():
        return direct
    if nested.exists():
        return nested
    raise SystemExit(f"missing {track}: expected {direct} or {nested}")


def _safe_counter(counter: Counter[str], key_name: str) -> list[dict[str, Any]]:
    return [{key_name: key, "count": int(value)} for key, value in sorted(counter.items(), key=lambda item: (-item[1], item[0]))]


def _quantiles(values: list[int]) -> dict[str, float | None]:
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


def _op_kind(op_name: str) -> str:
    return "filter" if op_name.endswith("_filter") else "mapper"


def _sequence_summary(sequence: list[str]) -> dict[str, int]:
    mapper_count = sum(1 for op_name in sequence if _op_kind(op_name) == "mapper")
    filter_count = len(sequence) - mapper_count
    return {
        "workflow_step_count": len(sequence),
        "mapper_step_count": mapper_count,
        "filter_step_count": filter_count,
    }


def _main_stats(rows: list[dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    domain_counts: Counter[str] = Counter()
    recipe_type_counts: Counter[str] = Counter()
    operator_counts: Counter[str] = Counter()
    reference_status_counts: Counter[str] = Counter()
    input_length_bucket_counts: Counter[str] = Counter()
    workflow_step_distribution: Counter[str] = Counter()
    mapper_step_distribution: Counter[str] = Counter()
    filter_step_distribution: Counter[str] = Counter()
    lengths: list[int] = []
    instance_rows: list[dict[str, Any]] = []

    for row in rows:
        domain = str(row.get("domain") or "unknown")
        recipe_type = str(row.get("recipe_type") or "unknown")
        reference_status = str(row.get("reference_status") or "unknown")
        input_length_chars = int(row.get("input_length_chars") or len(str(row.get("input_text") or "")))
        input_length_bucket = str(row.get("input_length_bucket") or "unknown")
        sequence = [str(op_name) for op_name in (row.get("operator_sequence") or [])]
        seq = _sequence_summary(sequence)

        domain_counts[domain] += 1
        recipe_type_counts[recipe_type] += 1
        reference_status_counts[reference_status] += 1
        input_length_bucket_counts[input_length_bucket] += 1
        workflow_step_distribution[str(seq["workflow_step_count"])] += 1
        mapper_step_distribution[str(seq["mapper_step_count"])] += 1
        filter_step_distribution[str(seq["filter_step_count"])] += 1
        for op_name in sequence:
            operator_counts[op_name] += 1
        lengths.append(input_length_chars)
        instance_rows.append(
            {
                "track": "main",
                "instance_id": row.get("instance_id"),
                "domain": domain,
                "recipe_id": row.get("recipe_id"),
                "recipe_variant_id": row.get("recipe_variant_id"),
                "recipe_type": recipe_type,
                "reference_status": reference_status,
                "input_length_chars": input_length_chars,
                "input_length_bucket": input_length_bucket,
                **seq,
            }
        )

    summary = {
        "instance_count": len(rows),
        "unique_recipe_ids": len({str(row.get("recipe_id")) for row in rows if row.get("recipe_id")}),
        "unique_recipe_variant_ids": len({str(row.get("recipe_variant_id")) for row in rows if row.get("recipe_variant_id")}),
        "domain_counts": _safe_counter(domain_counts, "domain"),
        "recipe_type_counts": _safe_counter(recipe_type_counts, "recipe_type"),
        "operator_counts": _safe_counter(operator_counts, "operator"),
        "reference_status_counts": _safe_counter(reference_status_counts, "reference_status"),
        "input_length_bucket_counts": _safe_counter(input_length_bucket_counts, "input_length_bucket"),
        "workflow_step_distribution": _safe_counter(workflow_step_distribution, "workflow_step_count"),
        "mapper_step_distribution": _safe_counter(mapper_step_distribution, "mapper_step_count"),
        "filter_step_distribution": _safe_counter(filter_step_distribution, "filter_step_count"),
        "input_length_stats": _quantiles(lengths),
    }
    return summary, instance_rows


def _order_stats(rows: list[dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    domain_counts: Counter[str] = Counter()
    recipe_type_counts: Counter[str] = Counter()
    operator_counts: Counter[str] = Counter()
    reference_status_counts: Counter[str] = Counter()
    order_slot_counts: Counter[str] = Counter()
    input_length_bucket_counts: Counter[str] = Counter()
    workflow_step_distribution: Counter[str] = Counter()
    lengths: list[int] = []
    instance_rows: list[dict[str, Any]] = []
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for row in rows:
        group_id = str(row.get("order_group_instance_id") or "")
        domain = str(row.get("domain") or "unknown")
        recipe_type = str(row.get("recipe_type") or "unknown")
        reference_status = str(row.get("reference_status") or "unknown")
        order_slot = str(row.get("order_slot") or "unknown")
        input_length_chars = int(row.get("input_length_chars") or len(str(row.get("input_text") or "")))
        input_length_bucket = str(row.get("input_length_bucket") or "unknown")
        sequence = [str(op_name) for op_name in (row.get("operator_sequence") or [])]
        seq = _sequence_summary(sequence)

        groups[group_id].append(row)
        domain_counts[domain] += 1
        recipe_type_counts[recipe_type] += 1
        reference_status_counts[reference_status] += 1
        order_slot_counts[order_slot] += 1
        input_length_bucket_counts[input_length_bucket] += 1
        workflow_step_distribution[str(seq["workflow_step_count"])] += 1
        for op_name in sequence:
            operator_counts[op_name] += 1
        lengths.append(input_length_chars)
        instance_rows.append(
            {
                "track": "order_sensitivity",
                "instance_id": row.get("instance_id"),
                "order_group_instance_id": group_id,
                "order_family_id": row.get("order_family_id"),
                "domain": domain,
                "recipe_id": row.get("recipe_id"),
                "recipe_variant_id": row.get("recipe_variant_id"),
                "recipe_type": recipe_type,
                "order_slot": order_slot,
                "reference_status": reference_status,
                "input_length_chars": input_length_chars,
                "input_length_bucket": input_length_bucket,
                **seq,
            }
        )

    distinct_signature_distribution: Counter[str] = Counter()
    domain_group_counts: Counter[str] = Counter()
    for group_id, group_rows in groups.items():
        if not group_id:
            continue
        domain = str(group_rows[0].get("domain") or "unknown")
        domain_group_counts[domain] += 1
        signatures = {
            (str(item.get("reference_status") or "unknown"), str(item.get("reference_text") or ""))
            for item in group_rows
        }
        distinct_signature_distribution[str(len(signatures))] += 1

    summary = {
        "instance_count": len(rows),
        "order_group_count": len([group_id for group_id in groups if group_id]),
        "order_family_count": len({str(row.get("order_family_id")) for row in rows if row.get("order_family_id")}),
        "domain_counts": _safe_counter(domain_counts, "domain"),
        "domain_group_counts": _safe_counter(domain_group_counts, "domain"),
        "recipe_type_counts": _safe_counter(recipe_type_counts, "recipe_type"),
        "operator_counts": _safe_counter(operator_counts, "operator"),
        "reference_status_counts": _safe_counter(reference_status_counts, "reference_status"),
        "order_slot_counts": _safe_counter(order_slot_counts, "order_slot"),
        "input_length_bucket_counts": _safe_counter(input_length_bucket_counts, "input_length_bucket"),
        "workflow_step_distribution": _safe_counter(workflow_step_distribution, "workflow_step_count"),
        "distinct_reference_count_per_group": _safe_counter(distinct_signature_distribution, "distinct_reference_count"),
        "input_length_stats": _quantiles(lengths),
    }
    return summary, instance_rows


def _atomic_stats(rows: list[dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    source_domain_counts: Counter[str] = Counter()
    operator_counts: Counter[str] = Counter()
    operator_kind_counts: Counter[str] = Counter()
    reference_status_counts: Counter[str] = Counter()
    input_length_bucket_counts: Counter[str] = Counter()
    lengths: list[int] = []
    instance_rows: list[dict[str, Any]] = []

    for row in rows:
        source_domain = str(row.get("source_domain") or row.get("domain") or "unknown")
        operator = str(row.get("operator") or "unknown")
        operator_kind = str(row.get("operator_kind") or _op_kind(operator))
        reference_status = str(row.get("reference_status") or "unknown")
        input_length_chars = int(row.get("input_length_chars") or len(str(row.get("input_text") or "")))
        input_length_bucket = str(row.get("input_length_bucket") or "unknown")

        source_domain_counts[source_domain] += 1
        operator_counts[operator] += 1
        operator_kind_counts[operator_kind] += 1
        reference_status_counts[reference_status] += 1
        input_length_bucket_counts[input_length_bucket] += 1
        lengths.append(input_length_chars)
        instance_rows.append(
            {
                "track": "atomic_ops",
                "instance_id": row.get("instance_id"),
                "source_domain": source_domain,
                "operator": operator,
                "operator_kind": operator_kind,
                "reference_status": reference_status,
                "input_length_chars": input_length_chars,
                "input_length_bucket": input_length_bucket,
            }
        )

    summary = {
        "instance_count": len(rows),
        "atomic_operator_count": len({str(row.get("operator")) for row in rows if row.get("operator")}),
        "source_domain_counts": _safe_counter(source_domain_counts, "source_domain"),
        "operator_counts": _safe_counter(operator_counts, "operator"),
        "operator_kind_counts": _safe_counter(operator_kind_counts, "operator_kind"),
        "reference_status_counts": _safe_counter(reference_status_counts, "reference_status"),
        "input_length_bucket_counts": _safe_counter(input_length_bucket_counts, "input_length_bucket"),
        "input_length_stats": _quantiles(lengths),
    }
    return summary, instance_rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Export compact benchmark statistics directly from benchmark jsonl files.")
    parser.add_argument("--benchmark-dir", default="data/benchmark")
    parser.add_argument("--output-dir", default="data/paper_stats/track_statistics")
    args = parser.parse_args()

    benchmark_dir = (ROOT / args.benchmark_dir).resolve()
    output_dir = (ROOT / args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    main_rows = _read_jsonl(_track_path(benchmark_dir, "main"))
    order_rows = _read_jsonl(_track_path(benchmark_dir, "order_sensitivity"))
    atomic_rows = _read_jsonl(_track_path(benchmark_dir, "atomic_ops"))

    main_summary, main_instance_rows = _main_stats(main_rows)
    order_summary, order_instance_rows = _order_stats(order_rows)
    atomic_summary, atomic_instance_rows = _atomic_stats(atomic_rows)

    overview = {
        "benchmark_dir": str(benchmark_dir),
        "main": main_summary,
        "order_sensitivity": order_summary,
        "atomic_ops": atomic_summary,
    }

    _write_json(output_dir / "track_statistics_summary.json", overview)
    _write_csv(output_dir / "main_instance_stats.csv", main_instance_rows)
    _write_csv(output_dir / "order_instance_stats.csv", order_instance_rows)
    _write_csv(output_dir / "atomic_instance_stats.csv", atomic_instance_rows)

    print(f"wrote summary -> {output_dir / 'track_statistics_summary.json'}", flush=True)
    print(f"wrote main instances -> {output_dir / 'main_instance_stats.csv'}", flush=True)
    print(f"wrote order instances -> {output_dir / 'order_instance_stats.csv'}", flush=True)
    print(f"wrote atomic instances -> {output_dir / 'atomic_instance_stats.csv'}", flush=True)


if __name__ == "__main__":
    main()
