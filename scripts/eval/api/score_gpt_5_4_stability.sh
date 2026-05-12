#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
cd "${REPO_ROOT}"

PYTHON_BIN="${REPO_ROOT}/.venv-ops/bin/python"
if [[ ! -x "${PYTHON_BIN}" ]]; then
  PYTHON_BIN="python3"
fi

TRACKS="${TRACKS:-atomic_ops,main,order_sensitivity}"
PREDICTIONS_ROOT="${PREDICTIONS_ROOT:-data/evaluation}"
MODEL_DIRNAME="${MODEL_DIRNAME:-gpt_5_4}"
PROMPT_MODE="${PROMPT_MODE:-direct}"
PREDICTIONS_FILENAME="${PREDICTIONS_FILENAME:-predictions_${PROMPT_MODE}.jsonl}"
SEED="${SEED:-0}"
K_VALUES="${K_VALUES:-1 2 3 4 5}"
PROGRESS_EVERY="${PROGRESS_EVERY:-20}"
RESUME="${RESUME:-true}"

for k in ${K_VALUES}; do
  score_dirname="score_${PROMPT_MODE}_k${k}_seed${SEED}"
  cmd=(
    "${REPO_ROOT}/scripts/score_benchmark_tracks.sh"
    --tracks "${TRACKS}"
    --predictions-root "${PREDICTIONS_ROOT}"
    --model-dirname "${MODEL_DIRNAME}"
    --predictions-filename "${PREDICTIONS_FILENAME}"
    --score-dirname "${score_dirname}"
    --prompt-variant-sample-size "${k}"
    --prompt-variant-sampling-seed "${SEED}"
    --progress-every "${PROGRESS_EVERY}"
  )
  if [[ "${RESUME}" == "true" ]]; then
    cmd+=(--resume)
  fi

  echo "[run] model=${MODEL_DIRNAME} prompt_mode=${PROMPT_MODE} k=${k} seed=${SEED}"
  "${cmd[@]}"
done

export PYTHONPATH="${REPO_ROOT}/src${PYTHONPATH:+:${PYTHONPATH}}"
"${PYTHON_BIN}" - <<'PY'
from __future__ import annotations

import json
import os
from pathlib import Path

tracks = [part.strip() for part in os.environ["TRACKS"].split(",") if part.strip()]
predictions_root = Path(os.environ["PREDICTIONS_ROOT"]).resolve()
model_dirname = os.environ["MODEL_DIRNAME"]
prompt_mode = os.environ["PROMPT_MODE"]
seed = int(os.environ["SEED"])
k_values = [int(part) for part in os.environ["K_VALUES"].split() if part.strip()]

print()
print(f"Model: {model_dirname}")
print(f"Predictions root: {predictions_root}")
print(f"Prompt mode: {prompt_mode}")
print(f"Seed: {seed}")
print()

for track in tracks:
    print(f"[track] {track}")
    header = ["k", "mean_rs@k", "mean_rs_strict@k", "mean_rg"]
    if track == "order_sensitivity":
        header.extend(["ocs_at_k", "rs_pre@k", "rs_mid@k", "rs_post@k"])
    print("\t".join(header))
    for k in k_values:
        paper_metrics_path = (
            predictions_root
            / track
            / model_dirname
            / f"score_{prompt_mode}_k{k}_seed{seed}"
            / "paper_metrics.json"
        )
        if not paper_metrics_path.exists():
            raise SystemExit(f"Missing paper metrics: {paper_metrics_path}")
        payload = json.loads(paper_metrics_path.read_text())
        row = [
            str(k),
            f"{float(payload.get('mean_rs@k', 0.0)):.4f}",
            f"{float(payload.get('mean_rs_strict@k', 0.0)):.4f}",
            f"{float(payload.get('mean_rg', 0.0)):.4f}",
        ]
        if track == "order_sensitivity":
            row.extend(
                [
                    f"{float(payload.get('ocs_at_k', 0.0)):.4f}",
                    f"{float(payload.get('rs_pre@k', 0.0)):.4f}",
                    f"{float(payload.get('rs_mid@k', 0.0)):.4f}",
                    f"{float(payload.get('rs_post@k', 0.0)):.4f}",
                ]
            )
        print("\t".join(row))
    print()
PY
