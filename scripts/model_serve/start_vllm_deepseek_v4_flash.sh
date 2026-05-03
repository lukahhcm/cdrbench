#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODEL_PATH="${MODEL_PATH:-deepseek-ai/DeepSeek-V4-Flash}"
MODEL_NAME="${MODEL_NAME:-deepseek_v4_flash}"
PORT="${PORT:-8909}"
GPU_IDS="${GPU_IDS:-0,1}"
TP_SIZE="${TP_SIZE:-2}"
VLLM_USE_MODELSCOPE="${VLLM_USE_MODELSCOPE:-False}" \
  "${SCRIPT_DIR}/../start_vllm.sh" "${MODEL_PATH}" "${MODEL_NAME}" "${PORT}" "${GPU_IDS}" "${TP_SIZE}"
