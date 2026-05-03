#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODEL_PATH="${MODEL_PATH:-/mnt/workspace/hyc/models/gemma-4-31B-it}"
MODEL_NAME="${MODEL_NAME:-gemma-4-31B-it}"
PORT="${PORT:-8001}"
GPU_IDS="${GPU_IDS:-4,5,6,7}"
TP_SIZE="${TP_SIZE:-4}"
MAX_MODEL_LEN="${MAX_MODEL_LEN:-32768}"
MAX_NUM_BATCHED_TOKENS="${MAX_NUM_BATCHED_TOKENS:-32768}"
VLLM_USE_MODELSCOPE="${VLLM_USE_MODELSCOPE:-True}" \
MAX_MODEL_LEN="${MAX_MODEL_LEN}" \
MAX_NUM_BATCHED_TOKENS="${MAX_NUM_BATCHED_TOKENS}" \
  "${SCRIPT_DIR}/../start_vllm.sh" "${MODEL_PATH}" "${MODEL_NAME}" "${PORT}" "${GPU_IDS}" "${TP_SIZE}"
