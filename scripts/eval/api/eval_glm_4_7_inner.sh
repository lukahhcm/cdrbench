#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../.." && pwd)"
cd "${REPO_ROOT}"

TRACKS="${TRACKS:-atomic_ops,main,order_sensitivity}"
EVAL_ROOT="${EVAL_ROOT:-data/benchmark}"
MODEL="${MODEL:-glm-4.7-inner}"
PROMPT_API_KEY="${PROMPT_API_KEY:-true}"
API_KEY="${API_KEY:-}"
OUTPUT_ROOT="${OUTPUT_ROOT:-data/evaluation/infer/glm_4_7_inner}"
PROMPT_VARIANT_INDICES="${PROMPT_VARIANT_INDICES:-all}"
MAX_SAMPLES="${MAX_SAMPLES:-0}"
MAX_INPUT_CHARS="${MAX_INPUT_CHARS:-0}"
MAX_TOKENS="${MAX_TOKENS:-0}"
CONCURRENCY="${CONCURRENCY:-10}"
PROGRESS_EVERY="${PROGRESS_EVERY:-20}"
RESUME="${RESUME:-true}"

exec "${REPO_ROOT}/scripts/eval/run_model_eval.sh" "$@"
