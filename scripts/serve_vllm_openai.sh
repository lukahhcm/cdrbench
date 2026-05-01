#!/bin/bash

# vLLM Server Startup Script for Qwen3.5 Models
# Usage: bash scripts/serve_vllm_openai.sh <model_path> <model_name> [tp_size] [gpu_ids] [port]
# 
# 此脚本只负责启动 vLLM 服务，不执行 benchmark 推理
# benchmark 推理请单独运行: ./scripts/infer_benchmark_tracks.sh --model <model_name> --base-url <api_base>

# 参数解析
# MODEL_PATH="${1:-/mnt/workspace/shared/qwen/Qwen/Qwen3.5-0.8B}"
# MODEL_NAME="${2:-qwen3_5_0_8b}"
# TP_SIZE="${3:-1}"
# GPU_IDS="${4:-0}"
# PORT="${5:-8901}"

# MODEL_PATH="${1:-/mnt/workspace/shared/qwen/Qwen/Qwen3.5-2B}"
# MODEL_NAME="${2:-qwen3_5_2b}"
# TP_SIZE="${3:-1}"
# GPU_IDS="${4:-1}"
# PORT="${5:-8902}"

# MODEL_PATH="${1:-/mnt/workspace/shared/qwen/Qwen/Qwen3.5-4B}"
# MODEL_NAME="${2:-qwen3_5_4b}"
# TP_SIZE="${3:-1}"
# GPU_IDS="${4:-2}"
# PORT="${5:-8903}"

MODEL_PATH="${1:-/mnt/workspace/shared/qwen/Qwen/Qwen3.5-9B}"
MODEL_NAME="${2:-qwen3_5_9b}"
TP_SIZE="${3:-1}"
GPU_IDS="${4:-3}"
PORT="${5:-8904}"

export VLLM_USE_MODELSCOPE=True

echo "=========================================="
echo "🚀 启动 vLLM 服务"
echo "   模型路径: ${MODEL_PATH}"
echo "   模型名称: ${MODEL_NAME}"
echo "   Tensor Parallel: ${TP_SIZE}"
echo "   GPU IDs: ${GPU_IDS}"
echo "   端口: ${PORT}"
echo "=========================================="
echo ""
echo "💡 提示: 服务启动后，请在另一个终端运行:"
echo "   ./scripts/infer_benchmark_tracks.sh --model ${MODEL_NAME} --base-url http://127.0.0.1:${PORT}/v1 --api-key EMPTY --eval-root data/benchmark --output-root data/evaluation/infer/${MODEL_NAME} --resume"
echo ""

# 启动 vLLM 服务 (前台运行)
CUDA_VISIBLE_DEVICES=${GPU_IDS} python -m vllm.entrypoints.openai.api_server \
    --model "${MODEL_PATH}" \
    --served-model-name "${MODEL_NAME}" \
    --trust_remote_code \
    --tensor-parallel-size ${TP_SIZE} \
    --port ${PORT} \
    --disable-log-stats
