#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  replay_benchmark_analysis.sh [options]

Replay selected benchmark recipes and attach per-step intermediate text states.

Options:
  --benchmark-root <path>       Default: data/benchmark
  --output-root <path>          Default: data/benchmark_analysis
  --tracks <csv>                Default: atomic_ops,main,order_sensitivity
  --domains-config <path>       Default: configs/domains.yaml
  --recipe-library-dir <path>   Default: data/processed/recipe_library
  --on-mapper-error <mode>      raise or keep. Default: raise
  --progress-every <int>        Default: 100
  -h, --help                    Show help
EOF
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

PYTHON_BIN="${REPO_ROOT}/.venv-ops/bin/python"
if [[ ! -x "${PYTHON_BIN}" ]]; then
  PYTHON_BIN="python3"
fi

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

export PYTHONPATH="${REPO_ROOT}/src${PYTHONPATH:+:${PYTHONPATH}}"
"${PYTHON_BIN}" -m cdrbench.prepare_data.replay_benchmark_analysis "$@"
