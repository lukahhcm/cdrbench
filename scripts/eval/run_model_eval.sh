#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  run_model_eval.sh [infer|score|all]
  run_model_eval.sh --mode <infer|score|all>

Modes:
  infer   Run inference only, resuming from existing outputs and only rerunning request errors.
  score   Recompute scores only, replacing each track's entire score/ directory.
  all     Default. Run inference first, then recompute scores from scratch.

Configuration is provided by environment variables from thin model wrappers.
EOF
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "${REPO_ROOT}"

MODE="all"
if [[ $# -gt 0 ]]; then
  case "$1" in
    infer|score|all)
      MODE="$1"
      shift 1
      ;;
    --mode)
      MODE="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
  esac
fi

case "${MODE}" in
  infer|score|all)
    ;;
  *)
    echo "Unsupported mode: ${MODE}" >&2
    usage
    exit 1
    ;;
esac

TRACKS="${TRACKS:-atomic_ops,main,order_sensitivity}"
EVAL_ROOT="${EVAL_ROOT:-data/benchmark}"
MODEL="${MODEL:-}"
BASE_URL="${BASE_URL:-}"
API_KEY="${API_KEY:-}"
OUTPUT_ROOT="${OUTPUT_ROOT:-data/evaluation/infer}"
PREDICTIONS_ROOT="${PREDICTIONS_ROOT:-${OUTPUT_ROOT}}"
PROMPT_VARIANT_INDICES="${PROMPT_VARIANT_INDICES:-all}"
MAX_SAMPLES="${MAX_SAMPLES:-0}"
MAX_INPUT_CHARS="${MAX_INPUT_CHARS:-0}"
MAX_TOKENS="${MAX_TOKENS:-0}"
CONCURRENCY="${CONCURRENCY:-1}"
PROGRESS_EVERY="${PROGRESS_EVERY:-20}"
RESUME="${RESUME:-true}"

run_infer() {
  if [[ -z "${MODEL}" ]]; then
    echo "MODEL is required for infer mode." >&2
    exit 1
  fi

  cmd=(
    "${REPO_ROOT}/scripts/infer_benchmark_tracks.sh"
    --tracks "${TRACKS}"
    --eval-root "${EVAL_ROOT}"
    --model "${MODEL}"
    --output-root "${OUTPUT_ROOT}"
    --prompt-variant-indices "${PROMPT_VARIANT_INDICES}"
    --max-samples "${MAX_SAMPLES}"
    --max-input-chars "${MAX_INPUT_CHARS}"
    --max-tokens "${MAX_TOKENS}"
    --concurrency "${CONCURRENCY}"
    --progress-every "${PROGRESS_EVERY}"
  )
  if [[ -n "${BASE_URL}" ]]; then
    cmd+=(--base-url "${BASE_URL}")
  fi
  if [[ -n "${API_KEY}" ]]; then
    cmd+=(--api-key "${API_KEY}")
  fi
  if [[ "${RESUME}" == "true" ]]; then
    cmd+=(--resume)
  fi
  if [[ $# -gt 0 ]]; then
    cmd+=("$@")
  fi

  "${cmd[@]}"
}

remove_existing_scores() {
  IFS=',' read -r -a TRACK_LIST <<< "${TRACKS}"
  for track in "${TRACK_LIST[@]}"; do
    score_dir="${PREDICTIONS_ROOT}/${track}/score"
    rm -rf "${score_dir}"
  done
}

run_score() {
  remove_existing_scores

  cmd=(
    "${REPO_ROOT}/scripts/score_benchmark_tracks.sh"
    --tracks "${TRACKS}"
    --predictions-root "${PREDICTIONS_ROOT}"
    --progress-every "${PROGRESS_EVERY}"
  )
  if [[ $# -gt 0 ]]; then
    cmd+=("$@")
  fi

  "${cmd[@]}"
}

case "${MODE}" in
  infer)
    run_infer "$@"
    ;;
  score)
    run_score "$@"
    ;;
  all)
    run_infer
    run_score
    ;;
esac
