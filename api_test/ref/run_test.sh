#!/usr/bin/env bash
# 模型可用性测试入口脚本
# 用法: ./run_test.sh [自定义prompt]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# ── 定义要测试的模型列表 ───────────────────────────────────────
# 海外模型（走 eval.dashscope.aliyuncs.com）
OVERSEAS_MODELS=(
  "openai.gpt-5.4-2026-03-05"
  "openai.gpt-5.4-pro-2026-03-05"
  "vertex_ai.claude-sonnet-4-6"
  "vertex_ai.claude-opus-4-6"
  "vertex_ai.claude-opus-4-5-20251101"
  "vertex_ai.gemini-3.1-pro-preview"
  "vertex_ai.gemini-3-pro-preview"
  "ai_studio.gemini-3-pro-image-preview"
  "grok-4-1-fast-reasoning"
)

# 文档中列在 eval 平台的国内厂商模型
EVAL_DOMESTIC_MODELS=(
  "glm-4.7-inner"
  "glm-image"
  "z_ai.glm-5"
  "moonshot.kimi-k2.5"
)

# 新增国内模型（走 dashscope.aliyuncs.com 原生 endpoint）
DOMESTIC_MODELS=(
  "qwen3.6-max-preview"
  "qwen3.6-plus"
  "deepseek-v4-pro"
  "deepseek-v4-flash"
  "kimi-k2.6"
  "glm-5.1"
  "minimax-m2.7"
)

# 合并所有模型
ALL_MODELS=("${OVERSEAS_MODELS[@]}" "${EVAL_DOMESTIC_MODELS[@]}" "${DOMESTIC_MODELS[@]}")

# ── 读取 API Key（终端输入，不落盘） ───────────────────────────
read -rsp "请输入 DASHSCOPE_API_KEY: " DASHSCOPE_API_KEY
echo  # 换行

if [[ -z "$DASHSCOPE_API_KEY" ]]; then
  echo "错误: API Key 不能为空"
  exit 1
fi

# ── 可选：自定义 prompt ──────────────────────────────────────
PROMPT="${1:-你好，请用一句话介绍你自己。}"

# ── 生成时间戳作为输出文件名 ──────────────────────────────────
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
OUTPUT_FILE="${SCRIPT_DIR}/results_${TIMESTAMP}.json"

# ── 执行测试 ─────────────────────────────────────────────────
echo ""
echo "============================================================"
echo "  模型可用性测试"
echo "  海外模型: ${#OVERSEAS_MODELS[@]} 个 → eval.dashscope.aliyuncs.com"
echo "  Eval国内: ${#EVAL_DOMESTIC_MODELS[@]} 个 → eval.dashscope.aliyuncs.com"
echo "  原生国内: ${#DOMESTIC_MODELS[@]} 个 → dashscope.aliyuncs.com"
echo "  总计: ${#ALL_MODELS[@]} 个"
echo "  输出文件: ${OUTPUT_FILE}"
echo "============================================================"
echo ""

python3 "${SCRIPT_DIR}/test_models.py" \
  --api-key "$DASHSCOPE_API_KEY" \
  --models "${ALL_MODELS[@]}" \
  --prompt "$PROMPT" \
  --output "$OUTPUT_FILE"

exit_code=$?

echo ""
echo "测试完成，结果已保存到: ${OUTPUT_FILE}"
exit $exit_code
