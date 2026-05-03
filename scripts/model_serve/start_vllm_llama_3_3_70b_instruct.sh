#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODEL_PATH="${MODEL_PATH:-meta-llama/Llama-3.3-70B-Instruct}"
MODEL_NAME="${MODEL_NAME:-llama_3_3_70b_instruct}"
PORT="${PORT:-8907}"
GPU_IDS="${GPU_IDS:-0,1,2,3}"
TP_SIZE="${TP_SIZE:-4}"
VLLM_USE_MODELSCOPE="${VLLM_USE_MODELSCOPE:-False}" \
  "${SCRIPT_DIR}/../start_vllm.sh" "${MODEL_PATH}" "${MODEL_NAME}" "${PORT}" "${GPU_IDS}" "${TP_SIZE}"
