#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  score_and_plot_gpt_claude_stability.sh [--rerun-score]

Default behavior:
  1. Check whether score outputs already exist for:
     - gpt_5_4
     - claude_opus_4_5
     across:
     - atomic_ops
     - main
     - order_sensitivity
     and k in 1..5 with seed=0
  2. Reuse existing score folders when present
  3. Only score missing outputs
  4. Draw one combined trend plot

Options:
  --rerun-score   Recompute all score directories before plotting
  -h, --help      Show this help

Environment overrides:
  PREDICTIONS_ROOT      Default: data/evaluation
  PROMPT_MODE           Default: direct
  PREDICTIONS_FILENAME  Default: predictions_${PROMPT_MODE}.jsonl
  TRACKS                Default: atomic_ops,main,order_sensitivity
  MODEL_DIRNAMES        Default: gpt_5_4,claude_opus_4_5
  MODEL_LABELS          Default: GPT-5.4,Claude Opus 4.5
  K_VALUES              Default: 1 2 3 4 5
  SEED                  Default: 0
  PROGRESS_EVERY        Default: 20
  OUTPUT_DIR            Default: ${PREDICTIONS_ROOT}/stability_plots
EOF
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
cd "${REPO_ROOT}"

PYTHON_BIN="${REPO_ROOT}/.venv-ops/bin/python"
if [[ ! -x "${PYTHON_BIN}" ]]; then
  PYTHON_BIN="python3"
fi

PREDICTIONS_ROOT="${PREDICTIONS_ROOT:-data/evaluation}"
PROMPT_MODE="${PROMPT_MODE:-direct}"
PREDICTIONS_FILENAME="${PREDICTIONS_FILENAME:-predictions_${PROMPT_MODE}.jsonl}"
TRACKS="${TRACKS:-atomic_ops,main,order_sensitivity}"
MODEL_DIRNAMES="${MODEL_DIRNAMES:-gpt_5_4,claude_opus_4_5}"
MODEL_LABELS="${MODEL_LABELS:-GPT-5.4,Claude Opus 4.5}"
K_VALUES="${K_VALUES:-1 2 3 4 5}"
SEED="${SEED:-0}"
PROGRESS_EVERY="${PROGRESS_EVERY:-20}"
OUTPUT_DIR="${OUTPUT_DIR:-${PREDICTIONS_ROOT}/stability_plots}"
RERUN_SCORE="false"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --rerun-score)
      RERUN_SCORE="true"
      shift 1
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 1
      ;;
  esac
done

mkdir -p "${OUTPUT_DIR}"

IFS=',' read -r -a TRACK_ARRAY <<< "${TRACKS}"
IFS=',' read -r -a MODEL_DIRNAME_ARRAY <<< "${MODEL_DIRNAMES}"
IFS=',' read -r -a MODEL_LABEL_ARRAY <<< "${MODEL_LABELS}"

if [[ "${#MODEL_DIRNAME_ARRAY[@]}" -ne "${#MODEL_LABEL_ARRAY[@]}" ]]; then
  echo "MODEL_DIRNAMES and MODEL_LABELS must have the same length." >&2
  exit 1
fi

score_dirname_for_k() {
  local k="$1"
  printf 'score_%s_k%s_seed%s' "${PROMPT_MODE}" "${k}" "${SEED}"
}

score_exists_for_model_and_k() {
  local model_dirname="$1"
  local k="$2"
  local score_dirname
  score_dirname="$(score_dirname_for_k "${k}")"
  local track
  for track in "${TRACK_ARRAY[@]}"; do
    local paper_metrics_path="${PREDICTIONS_ROOT}/${track}/${model_dirname}/${score_dirname}/paper_metrics.json"
    if [[ ! -f "${paper_metrics_path}" ]]; then
      return 1
    fi
  done
  return 0
}

run_score_for_model_and_k() {
  local model_dirname="$1"
  local k="$2"
  local score_dirname
  score_dirname="$(score_dirname_for_k "${k}")"

  echo "[score] model=${model_dirname} tracks=${TRACKS} k=${k} seed=${SEED} score_dir=${score_dirname}"
  "${REPO_ROOT}/scripts/score_benchmark_tracks.sh" \
    --tracks "${TRACKS}" \
    --predictions-root "${PREDICTIONS_ROOT}" \
    --model-dirname "${model_dirname}" \
    --predictions-filename "${PREDICTIONS_FILENAME}" \
    --score-dirname "${score_dirname}" \
    --prompt-variant-sample-size "${k}" \
    --prompt-variant-sampling-seed "${SEED}" \
    --progress-every "${PROGRESS_EVERY}"
}

for model_dirname in "${MODEL_DIRNAME_ARRAY[@]}"; do
  for k in ${K_VALUES}; do
    if [[ "${RERUN_SCORE}" == "true" ]]; then
      run_score_for_model_and_k "${model_dirname}" "${k}"
      continue
    fi
    if score_exists_for_model_and_k "${model_dirname}" "${k}"; then
      echo "[skip] model=${model_dirname} k=${k} existing score folders detected"
    else
      run_score_for_model_and_k "${model_dirname}" "${k}"
    fi
  done
done

export PYTHONPATH="${REPO_ROOT}/src${PYTHONPATH:+:${PYTHONPATH}}"
export PREDICTIONS_ROOT PROMPT_MODE TRACKS MODEL_DIRNAMES MODEL_LABELS K_VALUES SEED OUTPUT_DIR
"${PYTHON_BIN}" - <<'PY'
from __future__ import annotations

import csv
import json
import os
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

predictions_root = Path(os.environ["PREDICTIONS_ROOT"]).resolve()
prompt_mode = os.environ["PROMPT_MODE"]
tracks = [part.strip() for part in os.environ["TRACKS"].split(",") if part.strip()]
model_dirnames = [part.strip() for part in os.environ["MODEL_DIRNAMES"].split(",") if part.strip()]
model_labels = [part.strip() for part in os.environ["MODEL_LABELS"].split(",") if part.strip()]
k_values = [int(part) for part in os.environ["K_VALUES"].split() if part.strip()]
seed = int(os.environ["SEED"])
output_dir = Path(os.environ["OUTPUT_DIR"]).resolve()
output_dir.mkdir(parents=True, exist_ok=True)

track_styles = {
    "atomic_ops": "-",
    "main": "--",
    "order_sensitivity": ":",
}
track_pretty = {
    "atomic_ops": "Atomic Ops",
    "main": "Main",
    "order_sensitivity": "Order Sensitivity",
}
model_colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728"]

rows: list[dict[str, object]] = []
series: dict[tuple[str, str], list[float]] = {}

for model_idx, (model_dirname, model_label) in enumerate(zip(model_dirnames, model_labels)):
    for track in tracks:
        values: list[float] = []
        for k in k_values:
            score_dirname = f"score_{prompt_mode}_k{k}_seed{seed}"
            paper_metrics_path = predictions_root / track / model_dirname / score_dirname / "paper_metrics.json"
            if not paper_metrics_path.exists():
                raise SystemExit(f"Missing paper metrics: {paper_metrics_path}")
            payload = json.loads(paper_metrics_path.read_text())
            metric_value = float(payload.get("mean_rs@k", 0.0))
            values.append(metric_value)
            rows.append(
                {
                    "model_dirname": model_dirname,
                    "model_label": model_label,
                    "track": track,
                    "k": k,
                    "mean_rs@k": metric_value,
                    "mean_rs_strict@k": float(payload.get("mean_rs_strict@k", 0.0)),
                    "mean_rg": float(payload.get("mean_rg", 0.0)),
                    "ocs_at_k": "" if payload.get("ocs_at_k") is None else float(payload.get("ocs_at_k", 0.0)),
                    "rs_pre@k": "" if payload.get("rs_pre@k") is None else float(payload.get("rs_pre@k", 0.0)),
                    "rs_mid@k": "" if payload.get("rs_mid@k") is None else float(payload.get("rs_mid@k", 0.0)),
                    "rs_post@k": "" if payload.get("rs_post@k") is None else float(payload.get("rs_post@k", 0.0)),
                }
            )
        series[(model_label, track)] = values

csv_path = output_dir / f"gpt_claude_stability_{prompt_mode}_seed{seed}.csv"
with csv_path.open("w", newline="") as handle:
    writer = csv.DictWriter(
        handle,
        fieldnames=[
            "model_dirname",
            "model_label",
            "track",
            "k",
            "mean_rs@k",
            "mean_rs_strict@k",
            "mean_rg",
            "ocs_at_k",
            "rs_pre@k",
            "rs_mid@k",
            "rs_post@k",
        ],
    )
    writer.writeheader()
    writer.writerows(rows)

fig, ax = plt.subplots(figsize=(9.6, 5.8))

for model_idx, model_label in enumerate(model_labels):
    color = model_colors[model_idx % len(model_colors)]
    for track in tracks:
        linestyle = track_styles.get(track, "-")
        y_values = series[(model_label, track)]
        ax.plot(
            k_values,
            y_values,
            color=color,
            linestyle=linestyle,
            linewidth=2.2,
            marker="o",
            markersize=5.5,
        )

ax.set_title("GPT-5.4 vs Claude Opus 4.5 Stability Across Tracks", fontsize=13)
ax.set_xlabel("k")
ax.set_ylabel("Mean RS@k")
ax.set_xticks(k_values)
ax.set_ylim(0.0, 1.0)
ax.grid(alpha=0.25, linewidth=0.7)

model_handles = [
    Line2D([0], [0], color=model_colors[idx % len(model_colors)], linewidth=2.4, marker="o", label=label)
    for idx, label in enumerate(model_labels)
]
track_handles = [
    Line2D([0], [0], color="#444444", linewidth=2.0, linestyle=track_styles.get(track, "-"), label=track_pretty.get(track, track))
    for track in tracks
]

legend_models = ax.legend(handles=model_handles, title="Model", loc="lower right")
ax.add_artist(legend_models)
ax.legend(handles=track_handles, title="Track", loc="lower center")

fig.tight_layout()

png_path = output_dir / f"gpt_claude_stability_{prompt_mode}_seed{seed}.png"
pdf_path = output_dir / f"gpt_claude_stability_{prompt_mode}_seed{seed}.pdf"
fig.savefig(png_path, dpi=220, bbox_inches="tight")
fig.savefig(pdf_path, bbox_inches="tight")
plt.close(fig)

print()
print(f"CSV: {csv_path}")
print(f"PNG: {png_path}")
print(f"PDF: {pdf_path}")
print()
for track in tracks:
    print(f"[track] {track}")
    print("model\tk\tmean_rs@k\tmean_rs_strict@k\tmean_rg\tocs_at_k")
    for model_label in model_labels:
        for row in rows:
            if row["track"] == track and row["model_label"] == model_label:
                print(
                    f"{row['model_label']}\t{row['k']}\t{row['mean_rs@k']:.4f}\t"
                    f"{row['mean_rs_strict@k']:.4f}\t{row['mean_rg']:.4f}\t{row['ocs_at_k']}"
                )
    print()
PY
