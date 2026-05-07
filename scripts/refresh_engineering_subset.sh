#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  refresh_engineering_subset.sh [options]

Replace compliance-failed samples in the current engineering benchmark subset
with later candidates from the full source pool.

Options:
  --track <atomic_ops|main|order_sensitivity>  Track to refresh. Required
  --benchmark-dir <path>                       Current benchmark root. Default: data/benchmark
  --source-dir <path>                          Full benchmark root. Default: data/benchmark_full
  --output-dir <path>                          Optional output track dir. Default: overwrite current track dir
  --bad-instance-id <id>                       One bad instance_id to replace; repeatable
  --bad-instance-ids-file <path>               Text file with one bad instance_id per line
  --predictions-path <path>                    predictions.jsonl; auto-detect compliance-failed rows
  -h, --help                                   Show this help
EOF
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

PYTHON_BIN="$REPO_ROOT/.venv-ops/bin/python"
if [[ ! -x "$PYTHON_BIN" ]]; then
  PYTHON_BIN="python3"
fi

TRACK=""
BENCHMARK_DIR="data/benchmark"
SOURCE_DIR="data/benchmark_full"
OUTPUT_DIR=""
BAD_INSTANCE_IDS=()
BAD_INSTANCE_IDS_FILE=""
PREDICTIONS_PATH=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --track)
      TRACK="$2"
      shift 2
      ;;
    --benchmark-dir)
      BENCHMARK_DIR="$2"
      shift 2
      ;;
    --source-dir)
      SOURCE_DIR="$2"
      shift 2
      ;;
    --output-dir)
      OUTPUT_DIR="$2"
      shift 2
      ;;
    --bad-instance-id)
      BAD_INSTANCE_IDS+=("$2")
      shift 2
      ;;
    --bad-instance-ids-file)
      BAD_INSTANCE_IDS_FILE="$2"
      shift 2
      ;;
    --predictions-path)
      PREDICTIONS_PATH="$2"
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

if [[ -z "$TRACK" ]]; then
  echo "--track is required." >&2
  usage
  exit 1
fi

export PYTHONPATH="$REPO_ROOT/src${PYTHONPATH:+:$PYTHONPATH}"

cmd=(
  "$PYTHON_BIN" -m cdrbench.prepare_data.refresh_engineering_subset
  --track "$TRACK"
  --benchmark-dir "$BENCHMARK_DIR"
  --source-dir "$SOURCE_DIR"
)

if [[ -n "$OUTPUT_DIR" ]]; then
  cmd+=(--output-dir "$OUTPUT_DIR")
fi
for instance_id in "${BAD_INSTANCE_IDS[@]}"; do
  cmd+=(--bad-instance-id "$instance_id")
done
if [[ -n "$BAD_INSTANCE_IDS_FILE" ]]; then
  cmd+=(--bad-instance-ids-file "$BAD_INSTANCE_IDS_FILE")
fi
if [[ -n "$PREDICTIONS_PATH" ]]; then
  cmd+=(--predictions-path "$PREDICTIONS_PATH")
fi

"${cmd[@]}"
