#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def _load_jsonl_frame(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.DataFrame(_read_jsonl(path))


def _load_csv_frame(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def _safe_int(value: Any) -> int:
    if pd.isna(value):
        return 0
    return int(value)


def _safe_str(value: Any, default: str = "unknown") -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return default
    text = str(value)
    return text if text else default


def _table_to_markdown(df: pd.DataFrame) -> str:
    if df.empty:
        return "_empty_\n"
    frame = df.copy()
    frame.columns = [str(col) for col in frame.columns]
    rows = [[str(item) for item in row] for row in frame.itertuples(index=False, name=None)]
    headers = list(frame.columns)
    widths = [len(col) for col in headers]
    for row in rows:
        for idx, item in enumerate(row):
            widths[idx] = max(widths[idx], len(item))

    def fmt_row(items: list[str]) -> str:
        return "| " + " | ".join(item.ljust(widths[idx]) for idx, item in enumerate(items)) + " |"

    parts = [
        fmt_row(headers),
        "| " + " | ".join("-" * widths[idx] for idx in range(len(headers))) + " |",
    ]
    parts.extend(fmt_row(row) for row in rows)
    return "\n".join(parts) + "\n"


def _normalize_main_summary(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    out = df.copy()
    for col in [
        "candidate_count",
        "value_count",
        "keep_count",
        "drop_count",
        "selected_keep_count",
        "selected_drop_count",
        "selected_count",
    ]:
        if col in out.columns:
            out[col] = out[col].fillna(0).astype(int)
    return out


def _normalize_order_summary(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    out = df.copy()
    for col in [
        "candidate_count",
        "usable_record_count",
        "value_count",
        "selected_group_count",
        "selected_variant_count",
        "keep_count",
        "drop_count",
    ]:
        if col in out.columns:
            out[col] = out[col].fillna(0).astype(int)
    return out


def _normalize_atomic_summary(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    out = df.copy()
    for col in [
        "candidate_count",
        "value_count",
        "keep_count",
        "drop_count",
        "selected_count",
        "selected_keep_count",
        "selected_drop_count",
    ]:
        if col in out.columns:
            out[col] = out[col].fillna(0).astype(int)
    return out


def _build_overview(
    workflow_summary: pd.DataFrame,
    main_df: pd.DataFrame,
    order_df: pd.DataFrame,
    atomic_df: pd.DataFrame,
    main_summary: pd.DataFrame,
    order_summary: pd.DataFrame,
    atomic_summary: pd.DataFrame,
) -> dict[str, Any]:
    overview: dict[str, Any] = {}
    overview["library_domain_count"] = int(workflow_summary["domain"].nunique()) if "domain" in workflow_summary else 0
    overview["library_workflow_count"] = int(len(workflow_summary))
    overview["library_main_variant_count"] = int(workflow_summary.get("num_main_variants", pd.Series(dtype=int)).fillna(0).sum())
    overview["library_order_family_count"] = int(
        workflow_summary.get("num_order_sensitivity_families", pd.Series(dtype=int)).fillna(0).sum()
    )

    overview["main_instance_count"] = int(len(main_df))
    overview["main_kept_variant_count"] = int((main_summary.get("status", pd.Series(dtype=str)) == "kept").sum())
    overview["main_defined_variant_count"] = int(len(main_summary))

    overview["order_variant_instance_count"] = int(len(order_df))
    overview["order_group_count"] = int(order_df["order_group_instance_id"].nunique()) if "order_group_instance_id" in order_df else 0
    overview["order_kept_family_count"] = int((order_summary.get("status", pd.Series(dtype=str)) == "kept").sum())
    overview["order_defined_family_count"] = int(len(order_summary))

    overview["atomic_instance_count"] = int(len(atomic_df))
    overview["atomic_kept_operator_count"] = int((atomic_summary.get("status", pd.Series(dtype=str)) == "kept").sum())
    overview["atomic_defined_operator_count"] = int(len(atomic_summary))
    return overview


def _build_domain_summary(
    workflow_summary: pd.DataFrame,
    main_df: pd.DataFrame,
    order_df: pd.DataFrame,
    atomic_df: pd.DataFrame,
    main_summary: pd.DataFrame,
    order_summary: pd.DataFrame,
) -> pd.DataFrame:
    domains = set()
    for df, col in [
        (workflow_summary, "domain"),
        (main_df, "domain"),
        (order_df, "domain"),
        (atomic_df, "source_domain"),
        (main_summary, "domain"),
        (order_summary, "domain"),
    ]:
        if not df.empty and col in df.columns:
            domains.update(_safe_str(item) for item in df[col].dropna().tolist())

    rows: list[dict[str, Any]] = []
    for domain in sorted(domains):
        workflow_rows = workflow_summary[workflow_summary["domain"] == domain] if "domain" in workflow_summary else pd.DataFrame()
        main_rows = main_df[main_df["domain"] == domain] if "domain" in main_df else pd.DataFrame()
        order_rows = order_df[order_df["domain"] == domain] if "domain" in order_df else pd.DataFrame()
        atomic_rows = atomic_df[atomic_df["source_domain"] == domain] if "source_domain" in atomic_df else pd.DataFrame()
        main_summary_rows = main_summary[main_summary["domain"] == domain] if "domain" in main_summary else pd.DataFrame()
        order_summary_rows = order_summary[order_summary["domain"] == domain] if "domain" in order_summary else pd.DataFrame()

        rows.append(
            {
                "domain": domain,
                "workflow_count": int(len(workflow_rows)),
                "library_main_variants": int(workflow_rows.get("num_main_variants", pd.Series(dtype=int)).fillna(0).sum()),
                "library_order_families": int(
                    workflow_rows.get("num_order_sensitivity_families", pd.Series(dtype=int)).fillna(0).sum()
                ),
                "kept_main_variants": int((main_summary_rows.get("status", pd.Series(dtype=str)) == "kept").sum()),
                "kept_order_families": int((order_summary_rows.get("status", pd.Series(dtype=str)) == "kept").sum()),
                "main_instances": int(len(main_rows)),
                "main_clean_only_instances": int((main_rows.get("workflow_type", pd.Series(dtype=str)) == "clean-only").sum()),
                "main_filter_then_clean_instances": int(
                    (main_rows.get("workflow_type", pd.Series(dtype=str)) == "filter-then-clean").sum()
                ),
                "main_clean_then_filter_instances": int(
                    (main_rows.get("workflow_type", pd.Series(dtype=str)) == "clean-then-filter").sum()
                ),
                "order_variant_instances": int(len(order_rows)),
                "order_group_count": int(order_rows["order_group_instance_id"].nunique()) if "order_group_instance_id" in order_rows else 0,
                "atomic_instances": int(len(atomic_rows)),
            }
        )
    return pd.DataFrame(rows)


def _build_workflow_summary(
    workflow_summary: pd.DataFrame,
    main_df: pd.DataFrame,
    order_df: pd.DataFrame,
    main_summary: pd.DataFrame,
    order_summary: pd.DataFrame,
) -> pd.DataFrame:
    if workflow_summary.empty:
        return pd.DataFrame()

    main_instances = (
        main_df.groupby(["domain", "workflow_id"]).size().reset_index(name="main_instances")
        if {"domain", "workflow_id"}.issubset(main_df.columns)
        else pd.DataFrame(columns=["domain", "workflow_id", "main_instances"])
    )
    order_instances = (
        order_df.groupby(["domain", "workflow_id"]).size().reset_index(name="order_variant_instances")
        if {"domain", "workflow_id"}.issubset(order_df.columns)
        else pd.DataFrame(columns=["domain", "workflow_id", "order_variant_instances"])
    )
    order_groups = (
        order_df.groupby(["domain", "workflow_id"])["order_group_instance_id"]
        .nunique()
        .reset_index(name="order_group_count")
        if {"domain", "workflow_id", "order_group_instance_id"}.issubset(order_df.columns)
        else pd.DataFrame(columns=["domain", "workflow_id", "order_group_count"])
    )
    kept_main_variants = (
        main_summary[main_summary["status"] == "kept"]
        .groupby(["domain", "workflow_id"])
        .size()
        .reset_index(name="kept_main_variants")
        if {"domain", "workflow_id", "status"}.issubset(main_summary.columns)
        else pd.DataFrame(columns=["domain", "workflow_id", "kept_main_variants"])
    )
    kept_order_families = (
        order_summary[order_summary["status"] == "kept"]
        .groupby(["domain", "workflow_id"])
        .size()
        .reset_index(name="kept_order_families")
        if {"domain", "workflow_id", "status"}.issubset(order_summary.columns)
        else pd.DataFrame(columns=["domain", "workflow_id", "kept_order_families"])
    )

    out = workflow_summary.copy()
    for extra in [main_instances, order_instances, order_groups, kept_main_variants, kept_order_families]:
        out = out.merge(extra, on=["domain", "workflow_id"], how="left")
    for col in [
        "main_instances",
        "order_variant_instances",
        "order_group_count",
        "kept_main_variants",
        "kept_order_families",
    ]:
        if col in out.columns:
            out[col] = out[col].fillna(0).astype(int)
    return out.sort_values(["domain", "workflow_id"]).reset_index(drop=True)


def _build_main_variant_summary(main_summary: pd.DataFrame) -> pd.DataFrame:
    if main_summary.empty:
        return pd.DataFrame()
    cols = [
        "domain",
        "workflow_id",
        "workflow_variant_id",
        "workflow_type",
        "status",
        "candidate_count",
        "value_count",
        "keep_count",
        "drop_count",
        "selected_keep_count",
        "selected_drop_count",
        "selected_count",
        "filter_name",
    ]
    keep_cols = [col for col in cols if col in main_summary.columns]
    return main_summary[keep_cols].sort_values(["domain", "workflow_id", "workflow_variant_id"]).reset_index(drop=True)


def _build_order_family_summary(order_summary: pd.DataFrame) -> pd.DataFrame:
    if order_summary.empty:
        return pd.DataFrame()
    cols = [
        "domain",
        "workflow_id",
        "order_family_id",
        "filter_name",
        "status",
        "candidate_count",
        "usable_record_count",
        "value_count",
        "selected_group_count",
        "selected_variant_count",
        "keep_count",
        "drop_count",
    ]
    keep_cols = [col for col in cols if col in order_summary.columns]
    return order_summary[keep_cols].sort_values(["domain", "workflow_id", "order_family_id"]).reset_index(drop=True)


def _build_atomic_operator_summary(atomic_summary: pd.DataFrame) -> pd.DataFrame:
    if atomic_summary.empty:
        return pd.DataFrame()
    cols = [
        "operator",
        "operator_kind",
        "status",
        "candidate_count",
        "value_count",
        "keep_count",
        "drop_count",
        "selected_keep_count",
        "selected_drop_count",
        "selected_count",
        "source_domain_counts",
    ]
    keep_cols = [col for col in cols if col in atomic_summary.columns]
    return atomic_summary[keep_cols].sort_values(["operator_kind", "operator"]).reset_index(drop=True)


def _build_markdown_report(
    overview: dict[str, Any],
    domain_summary: pd.DataFrame,
    workflow_summary: pd.DataFrame,
    main_variant_summary: pd.DataFrame,
    order_family_summary: pd.DataFrame,
    atomic_operator_summary: pd.DataFrame,
) -> str:
    lines: list[str] = []
    lines.append("# CDR-Bench Paper Statistics")
    lines.append("")
    lines.append("## Overview")
    lines.append("")
    overview_df = pd.DataFrame(
        [{"metric": key, "value": value} for key, value in overview.items()]
    )
    lines.append(_table_to_markdown(overview_df))

    lines.append("## Per-Domain Summary")
    lines.append("")
    lines.append(_table_to_markdown(domain_summary))

    lines.append("## Per-Workflow Summary")
    lines.append("")
    lines.append(_table_to_markdown(workflow_summary))

    lines.append("## Main Variant Summary")
    lines.append("")
    lines.append(_table_to_markdown(main_variant_summary))

    lines.append("## Order Family Summary")
    lines.append("")
    lines.append(_table_to_markdown(order_family_summary))

    lines.append("## Atomic Operator Summary")
    lines.append("")
    lines.append(_table_to_markdown(atomic_operator_summary))
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize benchmark outputs into paper-ready benchmark statistics.")
    parser.add_argument("--benchmark-dir", default="data/benchmark")
    parser.add_argument("--workflow-library-dir", default="data/processed/workflow_library")
    parser.add_argument("--output-dir", default="data/paper_stats/benchmark")
    args = parser.parse_args()

    benchmark_dir = (ROOT / args.benchmark_dir).resolve()
    workflow_library_dir = (ROOT / args.workflow_library_dir).resolve()
    output_dir = (ROOT / args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    workflow_summary = _load_csv_frame(workflow_library_dir / "workflow_library_summary.csv")
    main_df = _load_jsonl_frame(benchmark_dir / "main.jsonl")
    order_df = _load_jsonl_frame(benchmark_dir / "order_sensitivity.jsonl")
    atomic_df = _load_jsonl_frame(benchmark_dir / "atomic_ops.jsonl")
    main_summary = _normalize_main_summary(_load_csv_frame(benchmark_dir / "main_summary.csv"))
    order_summary = _normalize_order_summary(_load_csv_frame(benchmark_dir / "order_sensitivity_summary.csv"))
    atomic_summary = _normalize_atomic_summary(_load_csv_frame(benchmark_dir / "atomic_ops_summary.csv"))

    overview = _build_overview(
        workflow_summary=workflow_summary,
        main_df=main_df,
        order_df=order_df,
        atomic_df=atomic_df,
        main_summary=main_summary,
        order_summary=order_summary,
        atomic_summary=atomic_summary,
    )
    domain_summary = _build_domain_summary(
        workflow_summary=workflow_summary,
        main_df=main_df,
        order_df=order_df,
        atomic_df=atomic_df,
        main_summary=main_summary,
        order_summary=order_summary,
    )
    workflow_level_summary = _build_workflow_summary(
        workflow_summary=workflow_summary,
        main_df=main_df,
        order_df=order_df,
        main_summary=main_summary,
        order_summary=order_summary,
    )
    main_variant_summary = _build_main_variant_summary(main_summary)
    order_family_summary = _build_order_family_summary(order_summary)
    atomic_operator_summary = _build_atomic_operator_summary(atomic_summary)

    (output_dir / "overview.json").write_text(
        json.dumps(overview, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    domain_summary.to_csv(output_dir / "domain_summary.csv", index=False)
    workflow_level_summary.to_csv(output_dir / "workflow_summary.csv", index=False)
    main_variant_summary.to_csv(output_dir / "main_variant_summary.csv", index=False)
    order_family_summary.to_csv(output_dir / "order_family_summary.csv", index=False)
    atomic_operator_summary.to_csv(output_dir / "atomic_operator_summary.csv", index=False)

    report = _build_markdown_report(
        overview=overview,
        domain_summary=domain_summary,
        workflow_summary=workflow_level_summary,
        main_variant_summary=main_variant_summary,
        order_family_summary=order_family_summary,
        atomic_operator_summary=atomic_operator_summary,
    )
    (output_dir / "paper_stats.md").write_text(report, encoding="utf-8")

    print(f"wrote paper stats -> {output_dir}", flush=True)


if __name__ == "__main__":
    main()
