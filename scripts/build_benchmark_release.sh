#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  build_benchmark_release.sh [options]

Build a release-friendly benchmark copy without replaying Data-Juicer operators.

Options:
  --benchmark-root <path>   Default: data/benchmark
  --output-root <path>      Default: data/benchmark_release
  --tracks <csv>            Default: atomic_ops,main,order_sensitivity
  --keep-replay             Preserve recipe_replay if present
  --atomic-operator-score-path <path>
                           Optional per-operator atomic RS CSV/JSON for difficulty
  --default-atomic-rs <x>   Fallback atomic RS for missing operators. Default: 0.5
  --progress-every <int>    Default: 1000
  -h, --help                Show help
EOF
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
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
"${PYTHON_BIN}" -m cdrbench.prepare_data.build_benchmark_release "$@"
