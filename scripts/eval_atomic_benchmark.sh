#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  eval_atomic_benchmark.sh [options]

Atomic-first benchmark helper. It supports two modes:

1. Online inference mode:
   Call an OpenAI-compatible API on the atomic eval file and score the output.

2. Score-only mode:
   If you already have model predictions from a server job, score them directly.

Options:
  --benchmark-path <path>          Atomic benchmark JSONL. Default: data/benchmark/atomic_ops.jsonl
  --eval-path <path>               Atomic eval-ready JSONL. Default: data/benchmark_prompts/atomic_ops/eval/atomic_ops.jsonl
  --predictions-path <path>        Existing prediction JSONL. If set, skip online inference and score this file directly.
  --output-dir <path>              Output directory. Default: data/eval_runs/atomic
  --model <name>                   API model name
  --base-url <url>                 API base URL
  --api-key <key>                  API key. For local vLLM you can use EMPTY.
  --prompt-variant-index <int>     Which prompt variant to use. Default: 0
  --max-samples <int>              Optional cap for smoke tests. Default: 0 (all)
  --temperature <float>            Default: 0.0
  --max-tokens <int>               Default: 4096
  --resume                         Resume online inference from an existing predictions file
  --prediction-status-field <key>  Score-only override for the prediction status field
  --prediction-text-field <key>    Score-only override for the prediction clean-text field
  -h, --help                       Show this help

Examples:
  ./scripts/eval_atomic_benchmark.sh \
    --model gpt-5.4 \
    --base-url http://123.57.212.178:3333/v1

  ./scripts/eval_atomic_benchmark.sh \
    --model Qwen/Qwen2.5-7B-Instruct \
    --base-url http://127.0.0.1:8000/v1 \
    --api-key EMPTY

  ./scripts/eval_atomic_benchmark.sh \
    --benchmark-path /mnt/bench/atomic_ops.jsonl \
    --predictions-path /mnt/runs/qwen_atomic_predictions.jsonl \
    --output-dir data/eval_runs/atomic_qwen_server
EOF
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

PYTHON_BIN="$REPO_ROOT/.venv-ops/bin/python"
if [[ ! -x "$PYTHON_BIN" ]]; then
  PYTHON_BIN="python3"
fi

BENCHMARK_PATH="data/benchmark/atomic_ops.jsonl"
EVAL_PATH="data/benchmark_prompts/atomic_ops/eval/atomic_ops.jsonl"
PREDICTIONS_PATH=""
OUTPUT_DIR="data/eval_runs/atomic"
MODEL=""
BASE_URL=""
API_KEY=""
PROMPT_VARIANT_INDEX="0"
MAX_SAMPLES="0"
TEMPERATURE="0.0"
MAX_TOKENS="4096"
RESUME="false"
PREDICTION_STATUS_FIELD=""
PREDICTION_TEXT_FIELD=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --benchmark-path)
      BENCHMARK_PATH="$2"
      shift 2
      ;;
    --eval-path)
      EVAL_PATH="$2"
      shift 2
      ;;
    --predictions-path)
      PREDICTIONS_PATH="$2"
      shift 2
      ;;
    --output-dir)
      OUTPUT_DIR="$2"
      shift 2
      ;;
    --model)
      MODEL="$2"
      shift 2
      ;;
    --base-url)
      BASE_URL="$2"
      shift 2
      ;;
    --api-key)
      API_KEY="$2"
      shift 2
      ;;
    --prompt-variant-index)
      PROMPT_VARIANT_INDEX="$2"
      shift 2
      ;;
    --max-samples)
      MAX_SAMPLES="$2"
      shift 2
      ;;
    --temperature)
      TEMPERATURE="$2"
      shift 2
      ;;
    --max-tokens)
      MAX_TOKENS="$2"
      shift 2
      ;;
    --resume)
      RESUME="true"
      shift 1
      ;;
    --prediction-status-field)
      PREDICTION_STATUS_FIELD="$2"
      shift 2
      ;;
    --prediction-text-field)
      PREDICTION_TEXT_FIELD="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 1
      ;;
  esac
done

mkdir -p "$OUTPUT_DIR"
export PYTHONPATH="$REPO_ROOT/src${PYTHONPATH:+:$PYTHONPATH}"

if [[ -n "$PREDICTIONS_PATH" ]]; then
  score_cmd=(
    "$PYTHON_BIN" -m cdrbench.eval.run_benchmark_eval score
    --predictions-path "$PREDICTIONS_PATH"
    --output-dir "$OUTPUT_DIR"
  )
  if [[ -n "$BENCHMARK_PATH" ]]; then
    score_cmd+=(--benchmark-path "$BENCHMARK_PATH")
  fi
  if [[ -n "$MODEL" ]]; then
    score_cmd+=(--model "$MODEL")
  fi
  if [[ -n "$BASE_URL" ]]; then
    score_cmd+=(--base-url "$BASE_URL")
  fi
  if [[ -n "$PREDICTION_STATUS_FIELD" ]]; then
    score_cmd+=(--prediction-status-field "$PREDICTION_STATUS_FIELD")
  fi
  if [[ -n "$PREDICTION_TEXT_FIELD" ]]; then
    score_cmd+=(--prediction-text-field "$PREDICTION_TEXT_FIELD")
  fi
  printf 'Scoring existing predictions: %s\n' "$PREDICTIONS_PATH"
  "${score_cmd[@]}"
  exit 0
fi

if [[ -z "$MODEL" ]]; then
  echo "--model is required in online inference mode." >&2
  exit 1
fi

predict_cmd=(
  "$PYTHON_BIN" -m cdrbench.eval.run_benchmark_eval predict
  --eval-path "$EVAL_PATH"
  --output-path "$OUTPUT_DIR/predictions.jsonl"
  --model "$MODEL"
  --prompt-variant-index "$PROMPT_VARIANT_INDEX"
  --max-samples "$MAX_SAMPLES"
  --temperature "$TEMPERATURE"
  --max-tokens "$MAX_TOKENS"
)

if [[ -n "$BASE_URL" ]]; then
  predict_cmd+=(--base-url "$BASE_URL")
fi
if [[ -n "$API_KEY" ]]; then
  predict_cmd+=(--api-key "$API_KEY")
fi
if [[ "$RESUME" == "true" ]]; then
  predict_cmd+=(--resume)
fi

printf 'Running atomic inference with model=%s\n' "$MODEL"
"${predict_cmd[@]}"

score_cmd=(
  "$PYTHON_BIN" -m cdrbench.eval.run_benchmark_eval score
  --predictions-path "$OUTPUT_DIR/predictions.jsonl"
  --output-dir "$OUTPUT_DIR/scored"
)
if [[ -n "$BENCHMARK_PATH" ]]; then
  score_cmd+=(--benchmark-path "$BENCHMARK_PATH")
fi
if [[ -n "$MODEL" ]]; then
  score_cmd+=(--model "$MODEL")
fi
if [[ -n "$BASE_URL" ]]; then
  score_cmd+=(--base-url "$BASE_URL")
fi

printf 'Scoring fresh predictions from %s\n' "$OUTPUT_DIR/predictions.jsonl"
"${score_cmd[@]}"
