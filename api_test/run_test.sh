#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

PYTHON_BIN="${REPO_ROOT}/.venv-ops/bin/python"
if [[ ! -x "${PYTHON_BIN}" ]]; then
  PYTHON_BIN="python3"
fi

SCRIPTS_DIR="${SCRIPTS_DIR:-${REPO_ROOT}/scripts/eval/infer/api}"
EVAL_PATH="${EVAL_PATH:-${REPO_ROOT}/data/benchmark/main/main.jsonl}"
PROMPT_CONFIG="${PROMPT_CONFIG:-${REPO_ROOT}/configs/recipe_prompting.yaml}"
PROMPT_VARIANT_INDEX="${PROMPT_VARIANT_INDEX:-0}"
TEMPERATURE="${TEMPERATURE:-0.0}"
TOP_P="${TOP_P:-0.0}"
MAX_TOKENS="${MAX_TOKENS:-0}"
TIMEOUT_SECONDS="${TIMEOUT_SECONDS:-300}"
MAX_RETRIES="${MAX_RETRIES:-4}"

API_KEY="${API_KEY:-${DASHSCOPE_API_KEY:-${OPENAI_API_KEY:-}}}"
if [[ -z "${API_KEY}" ]]; then
  read -rsp "请输入 API Key: " API_KEY
  echo
fi

if [[ -z "${API_KEY}" ]]; then
  echo "错误: API Key 不能为空" >&2
  exit 1
fi

TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
OUTPUT_FILE="${SCRIPT_DIR}/results_${TIMESTAMP}.json"

echo ""
echo "========================================================================"
echo "  API 推理冒烟测试"
echo "  脚本目录  : ${SCRIPTS_DIR}"
echo "  主数据文件: ${EVAL_PATH}"
echo "  Prompt配置: ${PROMPT_CONFIG}"
echo "  输出文件  : ${OUTPUT_FILE}"
echo "========================================================================"
echo ""

"${PYTHON_BIN}" "${SCRIPT_DIR}/test_models.py" \
  --api-key "${API_KEY}" \
  --scripts-dir "${SCRIPTS_DIR}" \
  --eval-path "${EVAL_PATH}" \
  --prompt-config "${PROMPT_CONFIG}" \
  --prompt-variant-index "${PROMPT_VARIANT_INDEX}" \
  --temperature "${TEMPERATURE}" \
  --top-p "${TOP_P}" \
  --max-tokens "${MAX_TOKENS}" \
  --timeout-seconds "${TIMEOUT_SECONDS}" \
  --max-retries "${MAX_RETRIES}" \
  --output "${OUTPUT_FILE}" \
  "$@"
