#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  plot_order_drop_scatter.sh --score-dir <score_dir> [--output-dir <dir>] [--model-label <label>]
  plot_order_drop_scatter.sh --scored-variants-path <path> [--output-dir <dir>] [--model-label <label>]

Examples:
  scripts/eval/plot_order_drop_scatter.sh \
    --score-dir data/evaluation/order_sensitivity/gpt_5_4/score_direct_k3_seed0

  scripts/eval/plot_order_drop_scatter.sh \
    --scored-variants-path data/evaluation/order_sensitivity/gpt_5_4/score_direct_k3_seed0/scored_variant_predictions.jsonl \
    --model-label GPT-5.4
EOF
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "${REPO_ROOT}"

PYTHON_BIN="${REPO_ROOT}/.venv-ops/bin/python"
if [[ ! -x "${PYTHON_BIN}" ]]; then
  PYTHON_BIN="python3"
fi

export PYTHONPATH="${REPO_ROOT}/src${PYTHONPATH:+:${PYTHONPATH}}"
"${PYTHON_BIN}" -m cdrbench.eval.plot_order_drop_scatter "$@"
