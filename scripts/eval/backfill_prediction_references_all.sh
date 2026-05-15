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
  --predictions-filename <n>   Optional exact filename to match.
  --prediction-glob <pattern>  Prediction filename glob. Can repeat. Default: prediction*.jsonl and predictions*.jsonl
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
PREDICTIONS_FILENAME=""
PREDICTION_GLOBS=()
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

find_prediction_files_for_track() {
  local track="$1"
  local track_predictions_root="${PREDICTIONS_ROOT}/${track}"
  local -a roots=()
  local -a found=()

  if [[ -n "${MODEL_DIRNAME}" ]]; then
    if [[ -d "${track_predictions_root}/${MODEL_DIRNAME}" ]]; then
      roots+=("${track_predictions_root}/${MODEL_DIRNAME}")
    fi
    if [[ -d "${PREDICTIONS_ROOT}/${MODEL_DIRNAME}" ]]; then
      roots+=("${PREDICTIONS_ROOT}/${MODEL_DIRNAME}")
    fi
  else
    if [[ -d "${track_predictions_root}" ]]; then
      roots+=("${track_predictions_root}")
    fi
    if [[ -d "${PREDICTIONS_ROOT}" ]]; then
      roots+=("${PREDICTIONS_ROOT}")
    fi
  fi

  if [[ "${#roots[@]}" -eq 0 ]]; then
    echo "[scan] track=${track} predictions_root_missing=${PREDICTIONS_ROOT}" >&2
    return 0
  fi

  for root in "${roots[@]}"; do
    for glob in "${PREDICTION_GLOBS[@]}"; do
      while IFS= read -r path; do
        case "/${path}" in
          */"${track}"/*)
            if [[ -z "${MODEL_DIRNAME}" || "/${path}" == */"${MODEL_DIRNAME}"/* ]]; then
              found+=("${path}")
            fi
            ;;
        esac
      done < <(find "${root}" -type f -name "${glob}" | sort)
    done
  done

  if [[ "${#found[@]}" -gt 0 ]]; then
    printf '%s\n' "${found[@]}" | awk '!seen[$0]++' | sort
  fi
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
    --prediction-glob)
      PREDICTION_GLOBS+=("$2")
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
if [[ -n "${PREDICTIONS_FILENAME}" ]]; then
  PREDICTION_GLOBS=("${PREDICTIONS_FILENAME}")
elif [[ "${#PREDICTION_GLOBS[@]}" -eq 0 ]]; then
  PREDICTION_GLOBS=('prediction*.jsonl' 'predictions*.jsonl')
fi

IFS=',' read -r -a TRACKS <<< "${TRACKS_CSV}"
total=0
for track in "${TRACKS[@]}"; do
  benchmark_path="$(resolve_benchmark_path "${track}")"
  mapfile -t prediction_files < <(find_prediction_files_for_track "${track}")
  echo "[scan] track=${track} benchmark=${benchmark_path} prediction_files=${#prediction_files[@]} globs=${PREDICTION_GLOBS[*]}"

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

if [[ "${total}" -eq 0 ]]; then
  cat >&2 <<EOF
No prediction files were backfilled.

Expected files like:
  ${PREDICTIONS_ROOT}/<track>/<model_dirname>/prediction*.jsonl

If your files use a different name pattern, pass:
  --prediction-glob '<pattern>'

If your evaluation root is different, pass:
  --predictions-root <path>

Quick checks:
  find ${PREDICTIONS_ROOT} -name 'predictions*.jsonl' | head
  find ${PREDICTIONS_ROOT} -name 'prediction*.jsonl' | head
EOF
  exit 1
fi

echo "[complete] backfilled prediction files: ${total}"
