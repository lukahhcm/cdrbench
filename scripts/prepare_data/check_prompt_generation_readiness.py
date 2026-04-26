#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cdrbench.llm_utils import resolve_model


TRACK_FILES = {
    "main": "main.jsonl",
    "order_sensitivity": "order_sensitivity.jsonl",
    "atomic_ops": "atomic_ops.jsonl",
}

DEFAULT_SKIPPED_OPERATORS = {"flagged_words_filter", "stopwords_filter"}


def _status(label: str, message: str) -> None:
    print(f"[{label}] {message}", flush=True)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def _operator_sequence(row: dict[str, Any]) -> list[str]:
    sequence = row.get("operator_sequence")
    if isinstance(sequence, list) and sequence:
        return [str(item) for item in sequence]
    operator = row.get("operator")
    return [str(operator)] if operator else []


def _check_track(path: Path, track: str, skipped_operators: set[str]) -> tuple[str, dict[str, Any]]:
    if not path.exists():
        return "FAIL", {"reason": f"missing file: {path}"}

    rows = _read_jsonl(path)
    if not rows:
        return "FAIL", {"reason": "file exists but contains no rows"}

    missing_input = 0
    missing_sequence = 0
    missing_filter_params = 0
    missing_track_name = 0
    missing_domain = 0
    skipped_rows = 0
    workflow_keys = set()
    operator_counter: Counter[str] = Counter()

    for row in rows:
        input_text = row.get("input_text")
        if not isinstance(input_text, str):
            missing_input += 1

        sequence = _operator_sequence(row)
        if not sequence:
            missing_sequence += 1
        else:
            operator_counter.update(sequence)

        if not isinstance(row.get("filter_params_by_name"), dict):
            missing_filter_params += 1

        if not row.get("benchmark_track"):
            missing_track_name += 1

        if not row.get("domain"):
            missing_domain += 1

        if any(op in skipped_operators for op in sequence):
            skipped_rows += 1

        workflow_keys.add(
            json.dumps(
                {
                    "track": row.get("benchmark_track"),
                    "domain": row.get("domain"),
                    "workflow_type": row.get("workflow_type"),
                    "order_slot": row.get("order_slot"),
                    "operator_sequence": sequence,
                    "filter_params_by_name": row.get("filter_params_by_name") or {},
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )

    issues = []
    if missing_input:
        issues.append(f"rows missing input_text={missing_input}")
    if missing_sequence:
        issues.append(f"rows missing operator_sequence/operator={missing_sequence}")
    if missing_filter_params:
        issues.append(f"rows missing filter_params_by_name={missing_filter_params}")
    if missing_track_name:
        issues.append(f"rows missing benchmark_track={missing_track_name}")
    if missing_domain:
        issues.append(f"rows missing domain={missing_domain}")

    if missing_input or missing_sequence:
        status = "FAIL"
    elif issues:
        status = "WARN"
    else:
        status = "PASS"

    return status, {
        "row_count": len(rows),
        "workflow_count": len(workflow_keys),
        "skipped_rows": skipped_rows,
        "top_operators": operator_counter.most_common(10),
        "issues": issues,
        "track": track,
        "path": str(path),
    }


def _check_llm_runtime() -> tuple[str, list[str]]:
    notes: list[str] = []

    try:
        import openai  # noqa: F401

        notes.append("python package `openai` is installed")
    except ImportError:
        notes.append("python package `openai` is missing")
        return "FAIL", notes

    key_is_set = any(os.getenv(name) for name in ("OPENAI_API_KEY", "DASHSCOPE_API_KEY", "API_KEY"))
    if key_is_set:
        notes.append("API key env is set")
    else:
        notes.append("API key env is not set")
        return "FAIL", notes

    base_url = os.getenv("OPENAI_BASE_URL") or os.getenv("LLM_BASE_URL")
    if base_url:
        notes.append("base URL env is set")
    else:
        notes.append("base URL env is not set; generator will use default")

    notes.append(f"resolved model: {resolve_model(None)}")
    return "PASS", notes


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Check whether server-side benchmark outputs are ready for prompt generation without printing raw input text."
    )
    parser.add_argument("--benchmark-dir", default="data/benchmark")
    parser.add_argument("--tracks", nargs="*", default=list(TRACK_FILES), choices=sorted(TRACK_FILES))
    parser.add_argument("--prompt-source", choices=["llm", "template"], default="llm")
    parser.add_argument(
        "--skip-operators",
        nargs="*",
        default=sorted(DEFAULT_SKIPPED_OPERATORS),
        help="Operators that the generator will skip by default.",
    )
    args = parser.parse_args()

    benchmark_dir = (ROOT / args.benchmark_dir).resolve()
    skipped_operators = set(args.skip_operators)

    print("== Prompt Generation Readiness Check ==", flush=True)
    print(f"benchmark_dir: {benchmark_dir}", flush=True)
    print(f"tracks: {', '.join(args.tracks)}", flush=True)
    print(f"prompt_source: {args.prompt_source}", flush=True)
    print(f"default skipped operators: {sorted(skipped_operators)}", flush=True)
    print("", flush=True)

    overall_status = "PASS"
    any_track_available = False

    for track in args.tracks:
        status, payload = _check_track(benchmark_dir / TRACK_FILES[track], track, skipped_operators)
        any_track_available = any_track_available or status in {"PASS", "WARN"}
        if status == "FAIL":
            overall_status = "FAIL"
        elif status == "WARN" and overall_status == "PASS":
            overall_status = "WARN"

        _status(status, f"track `{track}`")
        if "reason" in payload:
            print(f"  reason: {payload['reason']}", flush=True)
            continue
        print(f"  path: {payload['path']}", flush=True)
        print(f"  rows: {payload['row_count']}", flush=True)
        print(f"  unique workflows: {payload['workflow_count']}", flush=True)
        print(f"  rows skipped by default operator policy: {payload['skipped_rows']}", flush=True)
        if payload["issues"]:
            print("  issues:", flush=True)
            for issue in payload["issues"]:
                print(f"    - {issue}", flush=True)
        if payload["top_operators"]:
            print(f"  top operators: {payload['top_operators']}", flush=True)
        print("", flush=True)

    if not any_track_available and overall_status == "PASS":
        overall_status = "FAIL"

    if args.prompt_source == "llm":
        runtime_status, notes = _check_llm_runtime()
        if runtime_status == "FAIL":
            overall_status = "FAIL"
        elif runtime_status == "WARN" and overall_status == "PASS":
            overall_status = "WARN"
        _status(runtime_status, "llm runtime")
        for note in notes:
            print(f"  - {note}", flush=True)
        print("", flush=True)
    else:
        _status("PASS", "template prompt source selected; no LLM runtime check needed")
        print("", flush=True)

    if overall_status == "PASS":
        _status("PASS", "ready for prompt generation")
    elif overall_status == "WARN":
        _status("WARN", "can generate prompts, but review warnings first")
    else:
        _status("FAIL", "not ready for prompt generation")


if __name__ == "__main__":
    main()
