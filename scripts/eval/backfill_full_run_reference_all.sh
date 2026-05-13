#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  backfill_full_run_reference_all.sh --benchmark-path <benchmark_jsonl> [options]

Bulk-backfill reference_text_full_run into all order_sensitivity prediction files.

Options:
  --benchmark-path <path>         Order benchmark JSONL containing reference_text_full_run
  --predictions-root <path>       Default: data/evaluation/order_sensitivity
  --glob <pattern>                Default: predictions*.jsonl
  --overwrite                     Overwrite matched prediction files in place (default)
  --no-overwrite                  Write sibling *.with_full_run.jsonl files instead
  -h, --help                      Show help

Example:
  scripts/eval/backfill_full_run_reference_all.sh \
    --benchmark-path data/benchmark/order_sensitivity.jsonl \
    --predictions-root data/evaluation/order_sensitivity
EOF
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "${REPO_ROOT}"

BENCHMARK_PATH=""
PREDICTIONS_ROOT="data/evaluation/order_sensitivity"
GLOB_PATTERN="predictions*.jsonl"
OVERWRITE="true"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --benchmark-path)
      BENCHMARK_PATH="$2"
      shift 2
      ;;
    --predictions-root)
      PREDICTIONS_ROOT="$2"
      shift 2
      ;;
    --glob)
      GLOB_PATTERN="$2"
      shift 2
      ;;
    --overwrite)
      OVERWRITE="true"
      shift 1
      ;;
    --no-overwrite)
      OVERWRITE="false"
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

if [[ -z "${BENCHMARK_PATH}" ]]; then
  echo "--benchmark-path is required." >&2
  exit 1
fi

mapfile -t PREDICTION_FILES < <(find "${PREDICTIONS_ROOT}" -mindepth 2 -maxdepth 2 -type f -name "${GLOB_PATTERN}" | sort)

if [[ "${#PREDICTION_FILES[@]}" -eq 0 ]]; then
  echo "No prediction files found under ${PREDICTIONS_ROOT} matching ${GLOB_PATTERN}" >&2
  exit 1
fi

echo "[scan] found ${#PREDICTION_FILES[@]} prediction files under ${PREDICTIONS_ROOT}"

for predictions_path in "${PREDICTION_FILES[@]}"; do
  echo "[run] ${predictions_path}"
  cmd=(
    "${REPO_ROOT}/scripts/eval/backfill_full_run_reference.sh"
    --benchmark-path "${BENCHMARK_PATH}"
    --predictions-path "${predictions_path}"
  )
  if [[ "${OVERWRITE}" == "true" ]]; then
    cmd+=(--overwrite)
  fi
  "${cmd[@]}"
done

echo "[complete] bulk backfill finished"
