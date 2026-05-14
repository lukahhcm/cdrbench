#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  score_operator_progress.sh \
    --benchmark-analysis-path <benchmark_analysis_jsonl> \
    --predictions-path <predictions_jsonl> \
    --output-dir <output_dir> \
    [--track main] \
    [--text-match-mode exact|norm]

Scores per-operator progress on the compositional/main track without rerunning inference. Mapper completion is
based on idempotence: rerunning the DJ mapper on the model output no longer
changes the text. Filter completion is based on whether reevaluating the filter
on the model output matches the replayed filter status.
EOF
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "${REPO_ROOT}"

PYTHON_BIN="${PYTHON_BIN:-${REPO_ROOT}/.venv-ops/bin/python}"
if [[ ! -x "${PYTHON_BIN}" ]]; then
  PYTHON_BIN="python3"
fi

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

export PYTHONPATH="${REPO_ROOT}/src${PYTHONPATH:+:${PYTHONPATH}}"
"${PYTHON_BIN}" -m cdrbench.eval.score_operator_progress "$@"
