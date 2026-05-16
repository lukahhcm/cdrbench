#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml


ROOT = Path(__file__).resolve().parents[3]

TRACK_FILES = {
    "main": "main.jsonl",
    "order_sensitivity": "order_sensitivity.jsonl",
    "atomic_ops": "atomic_ops.jsonl",
}

PALETTE = {
    "web": "#4E79A7",
    "pii": "#E15759",
    "knowledge_base": "#59A14F",
    "arxiv": "#F28E2B",
    "clean-only": "#76B7B2",
    "filter-then-clean": "#EDC948",
    "clean-then-filter": "#B07AA1",
    "clean-filter-clean": "#FF9DA7",
    "short": "#8CD17D",
    "medium": "#4E79A7",
    "long": "#E15759",
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


def _latex_escape(text: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(ch, ch) for ch in text)


def _safe_counter_records(counter: Counter[str], key_name: str) -> list[dict[str, Any]]:
    return [{key_name: key, "count": int(value)} for key, value in sorted(counter.items(), key=lambda item: (-item[1], item[0]))]


def _quantiles(values: list[int | float]) -> dict[str, float | None]:
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


def _pct(count: int, total: int) -> str:
    if total <= 0:
        return "0.0\\%"
    return f"{(100.0 * count / total):.1f}\\%"


def _track_path(benchmark_root: Path, track: str) -> Path:
    direct = benchmark_root / TRACK_FILES[track]
    if direct.exists():
        return direct
    nested = benchmark_root / track / TRACK_FILES[track]
    if nested.exists():
        return nested
    raise SystemExit(f"missing track file for {track}: {direct} or {nested}")


def _load_recipe_library(path: Path) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]], dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    domains = payload.get("domains") or {}
    recipes_by_id: dict[str, dict[str, Any]] = {}
    main_variants_by_id: dict[str, dict[str, Any]] = {}
    order_variants_by_id: dict[str, dict[str, Any]] = {}
    families_by_id: dict[str, dict[str, Any]] = {}

    for domain_name, domain_payload in domains.items():
        for recipe in domain_payload.get("recipes") or []:
            recipe_id = str(recipe.get("recipe_id") or "")
            if recipe_id:
                recipes_by_id[recipe_id] = {"domain": domain_name, **recipe}
            for variant in recipe.get("main_recipe_variants") or []:
                variant_id = str(variant.get("recipe_variant_id") or "")
                if variant_id:
                    main_variants_by_id[variant_id] = {"domain": domain_name, "recipe_id": recipe_id, **variant}
            for variant in recipe.get("order_sensitivity_recipe_variants") or []:
                variant_id = str(variant.get("recipe_variant_id") or "")
                if variant_id:
                    order_variants_by_id[variant_id] = {"domain": domain_name, "recipe_id": recipe_id, **variant}
            for family in recipe.get("order_sensitivity_families") or []:
                family_id = str(family.get("order_family_id") or "")
                if family_id:
                    families_by_id[family_id] = {"domain": domain_name, "recipe_id": recipe_id, **family}
    return recipes_by_id, main_variants_by_id, order_variants_by_id, families_by_id


def _sequence_stats(sequence: list[str]) -> dict[str, int]:
    mapper_count = sum(1 for op_name in sequence if not str(op_name).endswith("_filter"))
    filter_count = len(sequence) - mapper_count
    return {
        "workflow_step_count": len(sequence),
        "mapper_step_count": mapper_count,
        "filter_step_count": filter_count,
    }


def _enrich_main_rows(rows: list[dict[str, Any]], variants_by_id: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    enriched: list[dict[str, Any]] = []
    for row in rows:
        variant_id = str(row.get("recipe_variant_id") or "")
        variant = variants_by_id.get(variant_id, {})
        sequence = [str(op_name) for op_name in (variant.get("operator_sequence") or [])]
        seq = _sequence_stats(sequence)
        enriched.append(
            {
                **row,
                "operator_sequence": sequence,
                "filter_name": variant.get("filter_name"),
                "filter_step_index": variant.get("filter_step_index"),
                **seq,
            }
        )
    return enriched


def _enrich_order_rows(
    rows: list[dict[str, Any]],
    variants_by_id: dict[str, dict[str, Any]],
    families_by_id: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    enriched: list[dict[str, Any]] = []
    for row in rows:
        variant_id = str(row.get("recipe_variant_id") or "")
        family_id = str(row.get("order_family_id") or "")
        variant = variants_by_id.get(variant_id, {})
        family = families_by_id.get(family_id, {})
        sequence = [str(op_name) for op_name in (variant.get("operator_sequence") or [])]
        seq = _sequence_stats(sequence)
        enriched.append(
            {
                **row,
                "operator_sequence": sequence,
                "filter_name": variant.get("filter_name") or family.get("filter_name"),
                "filter_step_index": variant.get("filter_step_index"),
                **seq,
            }
        )
    return enriched


def _summarize_main(rows: list[dict[str, Any]]) -> dict[str, Any]:
    domain_counts = Counter(str(row.get("domain") or "unknown") for row in rows)
    recipe_type_counts = Counter(str(row.get("recipe_type") or "unknown") for row in rows)
    status_counts = Counter(str(row.get("reference_status") or "unknown") for row in rows)
    input_bucket_counts = Counter(str(row.get("input_length_bucket") or "unknown") for row in rows)
    workflow_step_counts = Counter(str(int(row.get("workflow_step_count") or 0)) for row in rows)
    mapper_step_counts = Counter(str(int(row.get("mapper_step_count") or 0)) for row in rows)
    filter_step_counts = Counter(str(int(row.get("filter_step_count") or 0)) for row in rows)
    operator_counts: Counter[str] = Counter()
    for row in rows:
        for op_name in row.get("operator_sequence") or []:
            operator_counts[str(op_name)] += 1
    lengths = [int(row.get("input_length_chars") or 0) for row in rows]
    return {
        "instance_count": len(rows),
        "unique_recipe_ids": len({str(row.get("recipe_id")) for row in rows if row.get("recipe_id")}),
        "unique_recipe_variant_ids": len({str(row.get("recipe_variant_id")) for row in rows if row.get("recipe_variant_id")}),
        "domain_counts": _safe_counter_records(domain_counts, "domain"),
        "recipe_type_counts": _safe_counter_records(recipe_type_counts, "recipe_type"),
        "reference_status_counts": _safe_counter_records(status_counts, "reference_status"),
        "input_length_bucket_counts": _safe_counter_records(input_bucket_counts, "input_length_bucket"),
        "workflow_step_distribution": _safe_counter_records(workflow_step_counts, "workflow_step_count"),
        "mapper_step_distribution": _safe_counter_records(mapper_step_counts, "mapper_step_count"),
        "filter_step_distribution": _safe_counter_records(filter_step_counts, "filter_step_count"),
        "operator_counts": _safe_counter_records(operator_counts, "operator"),
        "input_length_stats": _quantiles(lengths),
    }


def _summarize_order(rows: list[dict[str, Any]]) -> dict[str, Any]:
    domain_counts = Counter(str(row.get("domain") or "unknown") for row in rows)
    domain_group_counts: Counter[str] = Counter()
    recipe_type_counts = Counter(str(row.get("recipe_type") or "unknown") for row in rows)
    status_counts = Counter(str(row.get("reference_status") or "unknown") for row in rows)
    slot_counts = Counter(str(row.get("order_slot") or "unknown") for row in rows)
    input_bucket_counts = Counter(str(row.get("input_length_bucket") or "unknown") for row in rows)
    workflow_step_counts = Counter(str(int(row.get("workflow_step_count") or 0)) for row in rows)
    operator_counts: Counter[str] = Counter()
    lengths = [int(row.get("input_length_chars") or 0) for row in rows]
    group_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        for op_name in row.get("operator_sequence") or []:
            operator_counts[str(op_name)] += 1
        group_id = str(row.get("order_group_instance_id") or "")
        if group_id:
            group_rows[group_id].append(row)
    distinct_reference_count: Counter[str] = Counter()
    for group_id, items in group_rows.items():
        domain = str(items[0].get("domain") or "unknown")
        domain_group_counts[domain] += 1
        signatures = {(str(item.get("reference_status") or "unknown"), str(item.get("reference_text") or "")) for item in items}
        distinct_reference_count[str(len(signatures))] += 1
    return {
        "instance_count": len(rows),
        "order_group_count": len(group_rows),
        "order_family_count": len({str(row.get("order_family_id")) for row in rows if row.get("order_family_id")}),
        "domain_counts": _safe_counter_records(domain_counts, "domain"),
        "domain_group_counts": _safe_counter_records(domain_group_counts, "domain"),
        "recipe_type_counts": _safe_counter_records(recipe_type_counts, "recipe_type"),
        "reference_status_counts": _safe_counter_records(status_counts, "reference_status"),
        "order_slot_counts": _safe_counter_records(slot_counts, "order_slot"),
        "input_length_bucket_counts": _safe_counter_records(input_bucket_counts, "input_length_bucket"),
        "workflow_step_distribution": _safe_counter_records(workflow_step_counts, "workflow_step_count"),
        "distinct_reference_count_per_group": _safe_counter_records(distinct_reference_count, "distinct_reference_count"),
        "operator_counts": _safe_counter_records(operator_counts, "operator"),
        "input_length_stats": _quantiles(lengths),
    }


def _summarize_atomic(rows: list[dict[str, Any]]) -> dict[str, Any]:
    source_domain_counts = Counter(str(row.get("source_domain") or row.get("domain") or "unknown") for row in rows)
    operator_counts = Counter(str(row.get("operator") or "unknown") for row in rows)
    operator_kind_counts = Counter(str(row.get("operator_kind") or "unknown") for row in rows)
    status_counts = Counter(str(row.get("reference_status") or "unknown") for row in rows)
    input_bucket_counts = Counter(str(row.get("input_length_bucket") or "unknown") for row in rows)
    lengths = [int(row.get("input_length_chars") or 0) for row in rows]
    return {
        "instance_count": len(rows),
        "atomic_operator_count": len({str(row.get("operator")) for row in rows if row.get("operator")}),
        "source_domain_counts": _safe_counter_records(source_domain_counts, "source_domain"),
        "operator_counts": _safe_counter_records(operator_counts, "operator"),
        "operator_kind_counts": _safe_counter_records(operator_kind_counts, "operator_kind"),
        "reference_status_counts": _safe_counter_records(status_counts, "reference_status"),
        "input_length_bucket_counts": _safe_counter_records(input_bucket_counts, "input_length_bucket"),
        "input_length_stats": _quantiles(lengths),
    }


def _instruction_stats(*track_rows: list[dict[str, Any]]) -> dict[str, Any]:
    prompt_variant_counts: list[int] = []
    prompt_word_counts: list[int] = []
    unique_prompt_keys: set[str] = set()
    for rows in track_rows:
        for row in rows:
            variants = row.get("prompt_variants") or []
            if isinstance(variants, list) and variants:
                prompt_variant_counts.append(len(variants))
                for variant in variants:
                    if not isinstance(variant, dict):
                        continue
                    prompt_key = str(row.get("recipe_prompt_key") or "")
                    style_id = str(variant.get("style_id") or "")
                    if prompt_key and style_id:
                        unique_prompt_keys.add(f"{prompt_key}::{style_id}")
                    user_requirement = str(variant.get("user_requirement") or "").strip()
                    if user_requirement:
                        prompt_word_counts.append(len(user_requirement.split()))
            else:
                prompt_variant_counts.append(int(row.get("prompt_variant_count") or 0))
    return {
        "avg_prompt_variants_per_sample": round(float(np.mean(prompt_variant_counts)), 2) if prompt_variant_counts else 0.0,
        "avg_instruction_words": round(float(np.mean(prompt_word_counts)), 1) if prompt_word_counts else 0.0,
        "median_instruction_words": round(float(np.median(prompt_word_counts)), 1) if prompt_word_counts else 0.0,
        "unique_prompt_variants": len(unique_prompt_keys),
    }


def _recipe_library_stats(
    recipes_by_id: dict[str, dict[str, Any]],
    main_variants_by_id: dict[str, dict[str, Any]],
    order_variants_by_id: dict[str, dict[str, Any]],
    families_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    family_ids = {str(recipe.get("family_id")) for recipe in recipes_by_id.values() if recipe.get("family_id")}
    recipe_clean_lengths = [len(recipe.get("ordered_clean_sequence") or []) for recipe in recipes_by_id.values()]
    main_variant_lengths = [len(variant.get("operator_sequence") or []) for variant in main_variants_by_id.values()]
    order_variant_lengths = [len(variant.get("operator_sequence") or []) for variant in order_variants_by_id.values()]
    all_operator_names = {
        *(str(op_name) for variant in main_variants_by_id.values() for op_name in (variant.get("operator_sequence") or [])),
        *(str(op_name) for variant in order_variants_by_id.values() for op_name in (variant.get("operator_sequence") or [])),
    }
    return {
        "recipe_family_count": len(family_ids),
        "unique_recipe_count": len(recipes_by_id),
        "main_variant_count": len(main_variants_by_id),
        "order_variant_count": len(order_variants_by_id),
        "order_family_count": len(families_by_id),
        "active_operator_count": len([name for name in all_operator_names if name]),
        "recipe_clean_length_stats": _quantiles(recipe_clean_lengths),
        "main_variant_length_stats": _quantiles(main_variant_lengths),
        "order_variant_length_stats": _quantiles(order_variant_lengths),
        "recipe_clean_length_distribution": _safe_counter_records(Counter(str(length) for length in recipe_clean_lengths), "recipe_clean_length"),
        "main_variant_length_distribution": _safe_counter_records(Counter(str(length) for length in main_variant_lengths), "workflow_step_count"),
        "order_variant_length_distribution": _safe_counter_records(Counter(str(length) for length in order_variant_lengths), "workflow_step_count"),
    }


def _count_value(records: list[dict[str, Any]], key_name: str, value: str) -> int:
    for record in records:
        if str(record.get(key_name)) == value:
            return int(record.get("count") or 0)
    return 0


def _render_summary_table(summary: dict[str, Any]) -> str:
    main = summary["main"]
    order = summary["order_sensitivity"]
    atomic = summary["atomic_ops"]
    recipe_library = summary["recipe_library"]
    instruction = summary["task_instruction"]
    total_instances = int(main["instance_count"]) + int(order["instance_count"]) + int(atomic["instance_count"])
    compositional_instances = int(main["instance_count"])
    avg_input_chars_all = (
        (
            float(main["input_length_stats"]["mean"] or 0.0) * int(main["instance_count"])
            + float(order["input_length_stats"]["mean"] or 0.0) * int(order["instance_count"])
            + float(atomic["input_length_stats"]["mean"] or 0.0) * int(atomic["instance_count"])
        )
        / total_instances
        if total_instances > 0
        else 0.0
    )
    overall_active_operator_count = max(
        int(recipe_library["active_operator_count"] or 0),
        int(atomic["atomic_operator_count"] or 0),
    )
    avg_recipe_length = float(recipe_library["main_variant_length_stats"]["mean"] or 0.0)
    median_input_chars_all = float(
        np.median(
            [
                int(row["input_length_chars"])
                for row in summary["main_rows_for_table"] + summary["order_rows_for_table"] + summary["atomic_rows_for_table"]
            ]
        )
    )
    lines = [
        r"\begin{table}[t]",
        r"\centering",
        r"\caption{High-level statistics of the released CDR-Bench subset.}",
        r"\label{tab:cdrbench-subset-stats}",
        r"\begin{tabular}{lr}",
        r"\toprule",
        r"\textbf{Statistics} & \textbf{Value} \\",
        r"\midrule",
        r"\textbf{Total Tasks} & \\",
        rf"- Total Tasks & {total_instances} (100\%) \\",
        rf"- Atomic Tasks & {int(atomic['instance_count'])} ({_pct(int(atomic['instance_count']), total_instances)}) \\",
        rf"- Compositional Tasks & {compositional_instances} ({_pct(compositional_instances, total_instances)}) \\",
        rf"- Order-Sensitivity Tasks & {int(order['instance_count'])} ({_pct(int(order['instance_count']), total_instances)}) \\",
        r"\midrule",
        r"\textbf{Input Text} & \\",
        rf"- Avg. Input Length (chars) & {avg_input_chars_all:.1f} \\",
        rf"- Median Input Length (chars) & {median_input_chars_all:.1f} \\",
        rf"- Short / Medium / Long Inputs & "
        rf"{_count_value(main['input_length_bucket_counts'], 'input_length_bucket', 'short') + _count_value(order['input_length_bucket_counts'], 'input_length_bucket', 'short') + _count_value(atomic['input_length_bucket_counts'], 'input_length_bucket', 'short')} / "
        rf"{_count_value(main['input_length_bucket_counts'], 'input_length_bucket', 'medium') + _count_value(order['input_length_bucket_counts'], 'input_length_bucket', 'medium') + _count_value(atomic['input_length_bucket_counts'], 'input_length_bucket', 'medium')} / "
        rf"{_count_value(main['input_length_bucket_counts'], 'input_length_bucket', 'long') + _count_value(order['input_length_bucket_counts'], 'input_length_bucket', 'long') + _count_value(atomic['input_length_bucket_counts'], 'input_length_bucket', 'long')} \\",
        r"\midrule",
        r"\textbf{Recipe Library} & \\",
        rf"- Active Operators Covered & {overall_active_operator_count} \\",
        rf"- Recipe Families & {int(recipe_library['recipe_family_count'])} \\",
        rf"- Unique Recipes & {int(recipe_library['unique_recipe_count'])} \\",
        rf"- Avg. Recipe Length & {avg_recipe_length:.2f} \\",
        r"\midrule",
        r"\textbf{Task Instruction} & \\",
        rf"- Avg. Prompt Variants Per Sample & {float(instruction['avg_prompt_variants_per_sample']):.2f} \\",
        rf"- Avg. Instruction Words & {float(instruction['avg_instruction_words']):.1f} \\",
        rf"- Median Instruction Words & {float(instruction['median_instruction_words']):.1f} \\",
        r"\bottomrule",
        r"\end{tabular}",
        r"\end{table}",
        "",
    ]
    return "\n".join(lines)


def _draw_bar(ax, labels: list[str], values: list[int], title: str, color: list[str] | str, *, horizontal: bool = False, xlabel: str = "Count") -> None:
    ax.set_title(title, fontsize=11, pad=10)
    if horizontal:
        y = np.arange(len(labels))
        bars = ax.barh(y, values, color=color)
        ax.set_yticks(y, labels, fontsize=9)
        ax.invert_yaxis()
        ax.set_xlabel(xlabel, fontsize=9)
        for bar, value in zip(bars, values):
            ax.text(value + max(values) * 0.01 if values else 0, bar.get_y() + bar.get_height() / 2, str(value), va="center", fontsize=8)
    else:
        x = np.arange(len(labels))
        bars = ax.bar(x, values, color=color)
        ax.set_xticks(x, labels, rotation=20, ha="right", fontsize=9)
        ax.set_ylabel(xlabel, fontsize=9)
        for bar, value in zip(bars, values):
            ax.text(bar.get_x() + bar.get_width() / 2, value, str(value), ha="center", va="bottom", fontsize=8)
    ax.grid(axis="y" if not horizontal else "x", alpha=0.2)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)


def _save_figure(fig, output_dir: Path, stem: str) -> None:
    fig.tight_layout()
    fig.savefig(output_dir / f"{stem}.png", dpi=220, bbox_inches="tight")
    fig.savefig(output_dir / f"{stem}.pdf", bbox_inches="tight")
    plt.close(fig)


def _plot_overview(summary: dict[str, Any], output_dir: Path) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    main = summary["main"]
    order = summary["order_sensitivity"]
    atomic = summary["atomic_ops"]

    domain_labels = ["web", "pii", "knowledge_base", "arxiv"]
    x = np.arange(len(domain_labels))
    width = 0.25
    main_vals = [_count_value(main["domain_counts"], "domain", label) for label in domain_labels]
    order_vals = [_count_value(order["domain_counts"], "domain", label) for label in domain_labels]
    atomic_vals = [_count_value(atomic["source_domain_counts"], "source_domain", label) for label in domain_labels]
    axes[0, 0].bar(x - width, main_vals, width, label="main", color="#4E79A7")
    axes[0, 0].bar(x, order_vals, width, label="order", color="#F28E2B")
    axes[0, 0].bar(x + width, atomic_vals, width, label="atomic", color="#59A14F")
    axes[0, 0].set_title("Domain Composition by Track", fontsize=11, pad=10)
    axes[0, 0].set_xticks(x, domain_labels, rotation=20, ha="right", fontsize=9)
    axes[0, 0].set_ylabel("Count", fontsize=9)
    axes[0, 0].legend(frameon=False, fontsize=8)
    axes[0, 0].grid(axis="y", alpha=0.2)

    recipe_labels = [item["recipe_type"] for item in main["recipe_type_counts"]]
    recipe_vals = [int(item["count"]) for item in main["recipe_type_counts"]]
    recipe_colors = [PALETTE.get(label, "#9C755F") for label in recipe_labels]
    _draw_bar(axes[0, 1], recipe_labels, recipe_vals, "Main Recipe Types", recipe_colors)

    bucket_labels = ["short", "medium", "long"]
    main_bucket = [_count_value(main["input_length_bucket_counts"], "input_length_bucket", label) for label in bucket_labels]
    order_bucket = [_count_value(order["input_length_bucket_counts"], "input_length_bucket", label) for label in bucket_labels]
    atomic_bucket = [_count_value(atomic["input_length_bucket_counts"], "input_length_bucket", label) for label in bucket_labels]
    bucket_x = np.arange(len(bucket_labels))
    axes[1, 0].bar(bucket_x - width, main_bucket, width, label="main", color="#4E79A7")
    axes[1, 0].bar(bucket_x, order_bucket, width, label="order", color="#F28E2B")
    axes[1, 0].bar(bucket_x + width, atomic_bucket, width, label="atomic", color="#59A14F")
    axes[1, 0].set_title("Input Length Buckets", fontsize=11, pad=10)
    axes[1, 0].set_xticks(bucket_x, bucket_labels, fontsize=9)
    axes[1, 0].set_ylabel("Count", fontsize=9)
    axes[1, 0].grid(axis="y", alpha=0.2)

    status_labels = ["KEEP", "DROP"]
    status_vals = [_count_value(main["reference_status_counts"], "reference_status", label) for label in status_labels]
    _draw_bar(axes[1, 1], status_labels, status_vals, "Main KEEP vs DROP", ["#8CD17D", "#E15759"])
    _save_figure(fig, output_dir, "subset_overview")


def _plot_structure(summary: dict[str, Any], output_dir: Path) -> None:
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    main = summary["main"]
    order = summary["order_sensitivity"]
    atomic = summary["atomic_ops"]
    recipe_library = summary["recipe_library"]

    main_step_labels = [item["workflow_step_count"] for item in main["workflow_step_distribution"]]
    main_step_vals = [int(item["count"]) for item in main["workflow_step_distribution"]]
    _draw_bar(axes[0, 0], main_step_labels, main_step_vals, "Main Workflow Steps", "#4E79A7")

    order_step_labels = [item["workflow_step_count"] for item in order["workflow_step_distribution"]]
    order_step_vals = [int(item["count"]) for item in order["workflow_step_distribution"]]
    _draw_bar(axes[0, 1], order_step_labels, order_step_vals, "Order Workflow Steps", "#F28E2B")

    distinct_labels = [item["distinct_reference_count"] for item in order["distinct_reference_count_per_group"]]
    distinct_vals = [int(item["count"]) for item in order["distinct_reference_count_per_group"]]
    _draw_bar(axes[1, 0], distinct_labels, distinct_vals, "Distinct References per Order Group", ["#59A14F", "#EDC948", "#E15759"])

    atomic_domain_labels = [item["source_domain"] for item in atomic["source_domain_counts"]]
    atomic_domain_vals = [int(item["count"]) for item in atomic["source_domain_counts"]]
    colors = [PALETTE.get(label, "#9C755F") for label in atomic_domain_labels]
    _draw_bar(axes[1, 1], atomic_domain_labels, atomic_domain_vals, "Atomic Source Domains", colors, horizontal=True)
    _save_figure(fig, output_dir, "subset_structure")

    fig2, axes2 = plt.subplots(1, 2, figsize=(11, 4))
    recipe_length_labels = [item["workflow_step_count"] for item in recipe_library["main_variant_length_distribution"]]
    recipe_length_vals = [int(item["count"]) for item in recipe_library["main_variant_length_distribution"]]
    _draw_bar(axes2[0], recipe_length_labels, recipe_length_vals, "Recipe Length Distribution", "#4E79A7")

    domain_labels = ["web", "pii", "knowledge_base", "arxiv"]
    x = np.arange(len(domain_labels))
    width = 0.35
    main_vals = [_count_value(main["domain_counts"], "domain", label) for label in domain_labels]
    order_vals = [_count_value(order["domain_counts"], "domain", label) for label in domain_labels]
    axes2[1].bar(x - width / 2, main_vals, width, label="compositional", color="#4E79A7")
    axes2[1].bar(x + width / 2, order_vals, width, label="order", color="#F28E2B")
    axes2[1].set_title("Domain Composition", fontsize=11, pad=10)
    axes2[1].set_xticks(x, domain_labels, rotation=20, ha="right", fontsize=9)
    axes2[1].set_ylabel("Count", fontsize=9)
    axes2[1].legend(frameon=False, fontsize=8)
    axes2[1].grid(axis="y", alpha=0.2)
    for spine in ("top", "right"):
        axes2[1].spines[spine].set_visible(False)
    _save_figure(fig2, output_dir, "subset_recipe_length_and_domains")


def main() -> None:
    parser = argparse.ArgumentParser(description="Render paper-ready subset benchmark statistics from bench_ref-style files.")
    parser.add_argument("--benchmark-root", default="bench_ref")
    parser.add_argument("--recipe-library", default="bench_ref/recipe_library.yaml")
    parser.add_argument("--output-dir", default="bench_ref/paper_stats")
    args = parser.parse_args()

    benchmark_root = (ROOT / args.benchmark_root).resolve()
    recipe_library_path = (ROOT / args.recipe_library).resolve()
    output_dir = (ROOT / args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    recipes_by_id, main_variants_by_id, order_variants_by_id, families_by_id = _load_recipe_library(recipe_library_path)
    main_rows = _enrich_main_rows(_read_jsonl(_track_path(benchmark_root, "main")), main_variants_by_id)
    order_rows = _enrich_order_rows(_read_jsonl(_track_path(benchmark_root, "order_sensitivity")), order_variants_by_id, families_by_id)
    atomic_rows = _read_jsonl(_track_path(benchmark_root, "atomic_ops"))

    missing_main_variants = sorted({str(row.get("recipe_variant_id") or "") for row in main_rows if row.get("recipe_variant_id") and not row.get("operator_sequence")})
    missing_order_variants = sorted({str(row.get("recipe_variant_id") or "") for row in order_rows if row.get("recipe_variant_id") and not row.get("operator_sequence")})
    if missing_main_variants or missing_order_variants:
        raise SystemExit(
            f"failed to recover operator sequences: missing_main={len(missing_main_variants)} missing_order={len(missing_order_variants)}"
        )

    summary = {
        "benchmark_root": str(benchmark_root),
        "recipe_library_path": str(recipe_library_path),
        "main": _summarize_main(main_rows),
        "order_sensitivity": _summarize_order(order_rows),
        "atomic_ops": _summarize_atomic(atomic_rows),
        "task_instruction": _instruction_stats(main_rows, order_rows, atomic_rows),
        "recipe_library": {
            **_recipe_library_stats(recipes_by_id, main_variants_by_id, order_variants_by_id, families_by_id),
            "domain_recipe_counts": {
                domain: len((payload.get("recipes") or []))
                for domain, payload in (yaml.safe_load(recipe_library_path.read_text(encoding="utf-8")).get("domains") or {}).items()
            }
        },
        "main_rows_for_table": [{"input_length_chars": int(row.get("input_length_chars") or 0)} for row in main_rows],
        "order_rows_for_table": [{"input_length_chars": int(row.get("input_length_chars") or 0)} for row in order_rows],
        "atomic_rows_for_table": [{"input_length_chars": int(row.get("input_length_chars") or 0)} for row in atomic_rows],
    }

    table_text = _render_summary_table(summary)
    (output_dir / "subset_statistics_table.tex").write_text(table_text, encoding="utf-8")
    _write_json(output_dir / "subset_statistics_summary.json", summary)
    _write_csv = lambda path, rows: pd.DataFrame(rows).to_csv(path, index=False)
    _write_csv(output_dir / "main_enriched_rows.csv", main_rows)
    _write_csv(output_dir / "order_enriched_rows.csv", order_rows)
    _write_csv(output_dir / "atomic_rows.csv", atomic_rows)
    _plot_overview(summary, output_dir)
    _plot_structure(summary, output_dir)

    print(f"wrote summary -> {output_dir / 'subset_statistics_summary.json'}", flush=True)
    print(f"wrote latex table -> {output_dir / 'subset_statistics_table.tex'}", flush=True)
    print(
        f"wrote figures -> {output_dir / 'subset_overview.png'}, "
        f"{output_dir / 'subset_structure.png'}, "
        f"{output_dir / 'subset_recipe_length_and_domains.png'}",
        flush=True,
    )


if __name__ == "__main__":
    main()
