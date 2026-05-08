#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  refresh_benchmark_references.sh [options]

Refresh deterministic reference fields in existing benchmark JSONL files
without rebuilding recipe libraries or reselection.

Options:
  --benchmark-root <path>   Existing benchmark root. Default: data/benchmark_full
  --output-root <path>      Optional alternate output root. Default: overwrite benchmark-root
  --tracks <csv>            Comma-separated tracks. Default: atomic_ops,main,order_sensitivity
  --domains-config <path>   Domains config YAML. Default: configs/domains.yaml
  --recipe-library-dir <path>  Recipe library root for backfilling missing operator sequences. Default: data/processed/recipe_library
  -h, --help                Show this help
EOF
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

PYTHON_BIN="$REPO_ROOT/.venv-ops/bin/python"
if [[ ! -x "$PYTHON_BIN" ]]; then
  PYTHON_BIN="python3"
fi

BENCHMARK_ROOT="data/benchmark_full"
OUTPUT_ROOT=""
TRACKS="atomic_ops,main,order_sensitivity"
DOMAINS_CONFIG="configs/domains.yaml"
RECIPE_LIBRARY_DIR="data/processed/recipe_library"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --benchmark-root)
      BENCHMARK_ROOT="$2"
      shift 2
      ;;
    --output-root)
      OUTPUT_ROOT="$2"
      shift 2
      ;;
    --tracks)
      TRACKS="$2"
      shift 2
      ;;
    --domains-config)
      DOMAINS_CONFIG="$2"
      shift 2
      ;;
    --recipe-library-dir)
      RECIPE_LIBRARY_DIR="$2"
      shift 2
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

export PYTHONPATH="$REPO_ROOT/src${PYTHONPATH:+:$PYTHONPATH}"

cmd=(
  "$PYTHON_BIN" -m cdrbench.prepare_data.refresh_benchmark_references
  --benchmark-root "$BENCHMARK_ROOT"
  --tracks "$TRACKS"
  --domains-config "$DOMAINS_CONFIG"
  --recipe-library-dir "$RECIPE_LIBRARY_DIR"
)
if [[ -n "$OUTPUT_ROOT" ]]; then
  cmd+=(--output-root "$OUTPUT_ROOT")
fi

"${cmd[@]}"
