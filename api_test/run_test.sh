#!/usr/bin/env bash
# 模型可用性测试入口脚本

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

PYTHON_BIN="${REPO_ROOT}/.venv-ops/bin/python"
if [[ ! -x "${PYTHON_BIN}" ]]; then
  PYTHON_BIN="python3"
fi

OVERSEAS_MODELS=(
  "openai.gpt-5.4-2026-03-05"
  "openai.gpt-5.4-pro-2026-03-05"
  "aws.claude-sonnet-4-6"
  "aws.claude-opus-4-6"
  "aws.claude-opus-4-5-20251101"
  "vertex_ai.gemini-3.1-pro-preview"
  "vertex_ai.gemini-3-pro-preview"
  "grok-4-1-fast-non-reasoning"
)

EVAL_DOMESTIC_MODELS=(
  "z_ai.glm-5"
  "kimi-k2.5"
)

DOMESTIC_MODELS=(
  "qwen3.6-max-preview"
  "qwen3.6-plus"
  "deepseek-v4-pro"
  "deepseek-v4-flash"
  "kimi-k2.6"
  "minimax.MiniMax-M2.7"
  "xiaomi.mimo-v2.5"
)

ALL_MODELS=("${OVERSEAS_MODELS[@]}" "${EVAL_DOMESTIC_MODELS[@]}" "${DOMESTIC_MODELS[@]}")

EVAL_PATH="${EVAL_PATH:-${REPO_ROOT}/data/benchmark/main/main.jsonl}"

read -rsp "请输入 DASHSCOPE_API_KEY: " DASHSCOPE_API_KEY
echo

if [[ -z "${DASHSCOPE_API_KEY}" ]]; then
  echo "错误: API Key 不能为空" >&2
  exit 1
fi

TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
OUTPUT_FILE="${SCRIPT_DIR}/results_${TIMESTAMP}.json"

echo ""
echo "============================================================"
echo "  模型可用性测试"
echo "  海外模型: ${#OVERSEAS_MODELS[@]} 个 → eval.dashscope.aliyuncs.com"
echo "  Eval国内: ${#EVAL_DOMESTIC_MODELS[@]} 个 → eval.dashscope.aliyuncs.com"
echo "  原生国内: ${#DOMESTIC_MODELS[@]} 个 → dashscope.aliyuncs.com"
echo "  总计: ${#ALL_MODELS[@]} 个"
echo "  eval-path: ${EVAL_PATH}"
echo "  输出文件: ${OUTPUT_FILE}"
echo "============================================================"
echo ""

"${PYTHON_BIN}" "${SCRIPT_DIR}/test_models.py" \
  --api-key "${DASHSCOPE_API_KEY}" \
  --models "${ALL_MODELS[@]}" \
  --eval-path "${EVAL_PATH}" \
  --output "${OUTPUT_FILE}" \
  "$@"

exit_code=$?

echo ""
echo "测试完成，结果已保存到: ${OUTPUT_FILE}"
exit $exit_code
