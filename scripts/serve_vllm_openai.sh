#!/usr/bin/env bash
set -euo pipefail

# vLLM Server Startup Script for CDR-Bench
# Usage: bash scripts/serve_vllm_openai.sh <model_path> <model_name> [tp_size] [gpu_ids] [port]
#
# 此脚本只负责启动 vLLM 服务，不执行测评
# 测评请单独运行: ./scripts/infer_benchmark_tracks.sh --model <model_name> --base-url <api_base>

MODEL_PATH="${1:-/mnt/workspace/shared/qwen/Qwen/Qwen3.5-9B}"
MODEL_NAME="${2:-qwen3_5_9b}"
TP_SIZE="${3:-1}"
GPU_IDS="${4:-3}"
PORT="${5:-8904}"

HOST="${HOST:-0.0.0.0}"
API_KEY="${API_KEY:-EMPTY}"
DTYPE="${DTYPE:-auto}"
MAX_MODEL_LEN="${MAX_MODEL_LEN:-32768}"
GPU_MEMORY_UTILIZATION="${GPU_MEMORY_UTILIZATION:-0.92}"
TRUST_REMOTE_CODE="${TRUST_REMOTE_CODE:-true}"

export VLLM_USE_MODELSCOPE=True

if ! command -v vllm >/dev/null 2>&1; then
  echo "❌ vllm command not found. Please install vLLM first."
  exit 1
fi

echo "=========================================="
echo "🚀 启动 vLLM 服务"
echo "   模型路径: ${MODEL_PATH}"
echo "   模型名称: ${MODEL_NAME}"
echo "   Tensor Parallel: ${TP_SIZE}"
echo "   GPU IDs: ${GPU_IDS}"
echo "   Host: ${HOST}"
echo "   端口: ${PORT}"
echo "   API Base: http://${HOST}:${PORT}/v1"
echo "=========================================="
echo ""
echo "💡 提示: 服务启动后，请在另一个终端运行:"
echo "   ./scripts/infer_benchmark_tracks.sh --model ${MODEL_NAME} --base-url http://127.0.0.1:${PORT}/v1 --api-key EMPTY --eval-root data/benchmark_prompts --output-root data/evaluation/infer/${MODEL_NAME} --resume"
echo ""

cmd=(
  vllm serve "${MODEL_PATH}"
  --host "${HOST}"
  --port "${PORT}"
  --api-key "${API_KEY}"
  --dtype "${DTYPE}"
  --served-model-name "${MODEL_NAME}"
  --tensor-parallel-size "${TP_SIZE}"
  --gpu-memory-utilization "${GPU_MEMORY_UTILIZATION}"
  --max-model-len "${MAX_MODEL_LEN}"
  --generation-config vllm
)

if [[ "${TRUST_REMOTE_CODE}" == "true" ]]; then
  cmd+=(--trust-remote-code)
fi

CUDA_VISIBLE_DEVICES="${GPU_IDS}" exec "${cmd[@]}"
