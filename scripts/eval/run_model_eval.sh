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
For API models, leave BASE_URL unset to auto-resolve the correct endpoint from the model config.
If PROMPT_API_KEY=true and API_KEY is empty, the script will prompt for a key before inference.
EOF
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "${REPO_ROOT}"

PYTHON_BIN="${REPO_ROOT}/.venv-ops/bin/python"
if [[ ! -x "${PYTHON_BIN}" ]]; then
  PYTHON_BIN="python3"
fi

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
PROMPT_API_KEY="${PROMPT_API_KEY:-false}"
OUTPUT_ROOT="${OUTPUT_ROOT:-data/evaluation/infer}"
PREDICTIONS_ROOT="${PREDICTIONS_ROOT:-${OUTPUT_ROOT}}"
PROMPT_VARIANT_INDICES="${PROMPT_VARIANT_INDICES:-all}"
MAX_SAMPLES="${MAX_SAMPLES:-0}"
MAX_INPUT_CHARS="${MAX_INPUT_CHARS:-0}"
MAX_TOKENS="${MAX_TOKENS:-0}"
CONCURRENCY="${CONCURRENCY:-1}"
PROGRESS_EVERY="${PROGRESS_EVERY:-20}"
RESUME="${RESUME:-true}"

prompt_for_api_key_if_needed() {
  if [[ "${PROMPT_API_KEY}" != "true" || -n "${API_KEY}" ]]; then
    return
  fi
  IFS= read -rsp "API key for ${MODEL}: " API_KEY
  echo
  if [[ -z "${API_KEY}" ]]; then
    echo "API key cannot be empty." >&2
    exit 1
  fi
}

run_infer() {
  if [[ -z "${MODEL}" ]]; then
    cat >&2 <<'EOF'
MODEL is required for infer mode.

Use a per-model wrapper for the default infer+score flow, for example:
  bash scripts/eval/api/eval_gpt_5_4.sh
  bash scripts/eval/api/eval_gpt_5_4.sh infer
  bash scripts/eval/api/eval_gpt_5_4.sh score

Or call the shared driver directly with MODEL set:
  MODEL=openai.gpt-5.4-2026-03-05 PROMPT_API_KEY=true bash scripts/eval/run_model_eval.sh
EOF
    exit 1
  fi

  prompt_for_api_key_if_needed

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
