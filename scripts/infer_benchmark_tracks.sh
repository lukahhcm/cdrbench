#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  infer_benchmark_tracks.sh [options]

Run model inference only for one or more CDR-Bench tracks.
By default this script targets all three benchmark tracks:

  1. atomic_ops
  2. main
  3. order_sensitivity

It stores raw model outputs so metrics can be recomputed later without rerunning inference.

Options:
  --eval-root <path>                   Benchmark root. Default: data/benchmark
  --output-root <path>                 Output root. Default: data/evaluation/infer
  --predictions-filename <name>        Predictions filename per track. Default: predictions.jsonl
  --tracks <csv>                       Comma-separated tracks. Default: atomic_ops,main,order_sensitivity
  --model <name>                       API model name. Required
  --base-url <url>                     OpenAI-compatible API base URL
  --api-key <key>                      API key. For local vLLM you can use EMPTY
  --prompt-variant-indices <spec>      Comma-separated indices or all. Default: all
  --prompt-mode <mode>                 Prompt construction mode. Default: direct
  --few-shot-source-root <path>        Full benchmark root for few-shot examples. Default: data/benchmark_full
  --max-samples <int>                  Optional cap for smoke tests. Default: 0 (all)
  --max-input-chars <int>              Skip inference for samples longer than this many chars. Default: 0 (disabled)
  --temperature <float>                Optional. Omitted by default.
  --top-p <float>                      Optional. Omitted by default.
  --max-tokens <int>                   Default: 0 (use model/server default)
  --concurrency <int>                  Request concurrency. Default: 1
  --progress-every <int>               Default: 20
  --resume                             Resume missing prompt variants from existing outputs
  --no-resume                          Disable resume even if a wrapper defaults it on
  -h, --help                           Show this help

Examples:
  ./scripts/infer_benchmark_tracks.sh \
    --model openai.gpt-5.4-2026-03-05 \
    --base-url https://eval.dashscope.aliyuncs.com/compatible-mode/v1 \
    --output-root data/evaluation/infer/gpt54

  ./scripts/infer_benchmark_tracks.sh \
    --model local-model \
    --base-url http://127.0.0.1:8000/v1 \
    --api-key EMPTY \
    --output-root data/evaluation/infer/local_model \
    --resume
EOF
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

PYTHON_BIN="$REPO_ROOT/.venv-ops/bin/python"
if [[ ! -x "$PYTHON_BIN" ]]; then
  PYTHON_BIN="python3"
fi

EVAL_ROOT="data/benchmark"
OUTPUT_ROOT="data/evaluation/infer"
PREDICTIONS_FILENAME="predictions.jsonl"
TRACKS_CSV="atomic_ops,main,order_sensitivity"
MODEL=""
BASE_URL=""
API_KEY=""
PROMPT_VARIANT_INDICES="all"
PROMPT_MODE="direct"
FEW_SHOT_SOURCE_ROOT="data/benchmark_full"
MAX_SAMPLES="0"
MAX_INPUT_CHARS="0"
TEMPERATURE=""
TOP_P=""
MAX_TOKENS="0"
CONCURRENCY="4"
PROGRESS_EVERY="20"
RESUME="false"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --eval-root)
      EVAL_ROOT="$2"
      shift 2
      ;;
    --output-root)
      OUTPUT_ROOT="$2"
      shift 2
      ;;
    --predictions-filename)
      PREDICTIONS_FILENAME="$2"
      shift 2
      ;;
    --tracks)
      TRACKS_CSV="$2"
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
    --prompt-variant-indices)
      PROMPT_VARIANT_INDICES="$2"
      shift 2
      ;;
    --prompt-mode)
      PROMPT_MODE="$2"
      shift 2
      ;;
    --few-shot-source-root)
      FEW_SHOT_SOURCE_ROOT="$2"
      shift 2
      ;;
    --max-samples)
      MAX_SAMPLES="$2"
      shift 2
      ;;
    --max-input-chars)
      MAX_INPUT_CHARS="$2"
      shift 2
      ;;
    --temperature)
      TEMPERATURE="$2"
      shift 2
      ;;
    --top-p)
      TOP_P="$2"
      shift 2
      ;;
    --max-tokens)
      MAX_TOKENS="$2"
      shift 2
      ;;
    --concurrency)
      CONCURRENCY="$2"
      shift 2
      ;;
    --progress-every)
      PROGRESS_EVERY="$2"
      shift 2
      ;;
    --resume)
      RESUME="true"
      shift 1
      ;;
    --no-resume)
      RESUME="false"
      shift 1
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

if [[ -z "$MODEL" ]]; then
  echo "--model is required." >&2
  exit 1
fi

export PYTHONPATH="$REPO_ROOT/src${PYTHONPATH:+:$PYTHONPATH}"
IFS=',' read -r -a TRACKS <<< "$TRACKS_CSV"

track_eval_path() {
  case "$1" in
    atomic_ops)
      printf '%s\n' "$EVAL_ROOT/atomic_ops/atomic_ops.jsonl"
      ;;
    main)
      printf '%s\n' "$EVAL_ROOT/main/main.jsonl"
      ;;
    order_sensitivity)
      printf '%s\n' "$EVAL_ROOT/order_sensitivity/order_sensitivity.jsonl"
      ;;
    *)
      echo "Unsupported track: $1" >&2
      exit 1
      ;;
  esac
}

for track in "${TRACKS[@]}"; do
  eval_path="$(track_eval_path "$track")"
  output_dir="$OUTPUT_ROOT/$track"
  mkdir -p "$output_dir"
  if [[ ! -f "$eval_path" ]]; then
    echo "Missing eval file for track=$track: $eval_path" >&2
    exit 1
  fi

  cmd=(
    "$PYTHON_BIN" -m cdrbench.eval.run_benchmark_infer
    --eval-path "$eval_path"
    --output-path "$output_dir/$PREDICTIONS_FILENAME"
    --model "$MODEL"
    --prompt-variant-indices "$PROMPT_VARIANT_INDICES"
    --prompt-mode "$PROMPT_MODE"
    --few-shot-source-root "$FEW_SHOT_SOURCE_ROOT"
    --max-samples "$MAX_SAMPLES"
    --max-input-chars "$MAX_INPUT_CHARS"
    --max-tokens "$MAX_TOKENS"
    --concurrency "$CONCURRENCY"
    --progress-every "$PROGRESS_EVERY"
  )
  if [[ -n "$TEMPERATURE" ]]; then
    cmd+=(--temperature "$TEMPERATURE")
  fi
  if [[ -n "$TOP_P" ]]; then
    cmd+=(--top-p "$TOP_P")
  fi
  if [[ -n "$BASE_URL" ]]; then
    cmd+=(--base-url "$BASE_URL")
  fi
  if [[ -n "$API_KEY" ]]; then
    cmd+=(--api-key "$API_KEY")
  fi
  if [[ "$RESUME" == "true" ]]; then
    cmd+=(--resume)
  fi

  echo "[run] track=$track step=infer output_dir=$output_dir"
  "${cmd[@]}"
  echo "[done] track=$track predictions=$output_dir/$PREDICTIONS_FILENAME"
done

echo "[complete] inference finished for tracks: ${TRACKS[*]}"
echo "[complete] outputs rooted at: $OUTPUT_ROOT"
