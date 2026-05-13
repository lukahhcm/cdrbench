#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  backfill_full_run_reference.sh \
    --benchmark-path <benchmark_jsonl> \
    --predictions-path <predictions_jsonl> \
    [--output-path <repaired_predictions_jsonl>]

  backfill_full_run_reference.sh \
    --benchmark-path <benchmark_jsonl> \
    --predictions-path <predictions_jsonl> \
    --overwrite
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
"${PYTHON_BIN}" -m cdrbench.eval.backfill_full_run_reference "$@"
