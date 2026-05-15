#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  backfill_prediction_references_all.sh --benchmark-root <root> [options]

Backfill refreshed benchmark/GT fields into existing prediction files without
rerunning inference. Prediction model outputs are preserved.

Options:
  --benchmark-root <path>      Root containing <track>.jsonl files. Required.
  --predictions-root <path>    Default: data/evaluation
  --tracks <csv>               Default: atomic_ops,main,order_sensitivity
  --model-dirname <name>       Optional: only update one model directory.
  --predictions-filename <n>   Default: predictions.jsonl
  --overwrite                  Overwrite prediction files in place. Default.
  --no-overwrite               Write sibling *.backfilled.jsonl files.
  --references-only            Only update reference_* fields.
  -h, --help                   Show help.

Example:
  scripts/eval/backfill_prediction_references_all.sh \
    --benchmark-root data/benchmark_release \
    --predictions-root data/evaluation \
    --model-dirname gpt_5_4
EOF
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "${REPO_ROOT}"

BENCHMARK_ROOT=""
PREDICTIONS_ROOT="data/evaluation"
TRACKS_CSV="atomic_ops,main,order_sensitivity"
MODEL_DIRNAME=""
PREDICTIONS_FILENAME="predictions.jsonl"
OVERWRITE="true"
REFERENCES_ONLY="false"

track_filename() {
  case "$1" in
    atomic_ops)
      printf 'atomic_ops.jsonl'
      ;;
    main)
      printf 'main.jsonl'
      ;;
    order_sensitivity)
      printf 'order_sensitivity.jsonl'
      ;;
    *)
      echo "Unsupported track: $1" >&2
      return 1
      ;;
  esac
}

resolve_benchmark_path() {
  local track="$1"
  local filename
  filename="$(track_filename "${track}")"
  local nested="${BENCHMARK_ROOT}/${track}/${filename}"
  local flat="${BENCHMARK_ROOT}/${filename}"
  if [[ -f "${nested}" ]]; then
    printf '%s\n' "${nested}"
    return 0
  fi
  if [[ -f "${flat}" ]]; then
    printf '%s\n' "${flat}"
    return 0
  fi
  echo "Missing benchmark file for track=${track}: expected ${nested} or ${flat}" >&2
  return 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --benchmark-root)
      BENCHMARK_ROOT="$2"
      shift 2
      ;;
    --predictions-root)
      PREDICTIONS_ROOT="$2"
      shift 2
      ;;
    --tracks)
      TRACKS_CSV="$2"
      shift 2
      ;;
    --model-dirname)
      MODEL_DIRNAME="$2"
      shift 2
      ;;
    --predictions-filename)
      PREDICTIONS_FILENAME="$2"
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
    --references-only)
      REFERENCES_ONLY="true"
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

if [[ -z "${BENCHMARK_ROOT}" ]]; then
  echo "--benchmark-root is required." >&2
  exit 1
fi

IFS=',' read -r -a TRACKS <<< "${TRACKS_CSV}"
total=0
for track in "${TRACKS[@]}"; do
  benchmark_path="$(resolve_benchmark_path "${track}")"

  if [[ -n "${MODEL_DIRNAME}" ]]; then
    prediction_files=("${PREDICTIONS_ROOT}/${track}/${MODEL_DIRNAME}/${PREDICTIONS_FILENAME}")
  else
    mapfile -t prediction_files < <(find "${PREDICTIONS_ROOT}/${track}" -mindepth 2 -maxdepth 2 -type f -name "${PREDICTIONS_FILENAME}" | sort)
  fi

  for predictions_path in "${prediction_files[@]}"; do
    if [[ ! -f "${predictions_path}" ]]; then
      echo "Missing predictions file: ${predictions_path}" >&2
      exit 1
    fi
    echo "[backfill] track=${track} predictions=${predictions_path}"
    cmd=(
      "${REPO_ROOT}/scripts/eval/backfill_prediction_references.sh"
      --benchmark-path "${benchmark_path}"
      --predictions-path "${predictions_path}"
    )
    if [[ "${OVERWRITE}" == "true" ]]; then
      cmd+=(--overwrite)
    fi
    if [[ "${REFERENCES_ONLY}" == "true" ]]; then
      cmd+=(--references-only)
    fi
    "${cmd[@]}"
    total=$((total + 1))
  done
done

echo "[complete] backfilled prediction files: ${total}"
