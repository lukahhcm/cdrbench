#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  serve_vllm_openai.sh --model <hf_or_local_path> [options] [-- extra_vllm_args...]

Launch a local OpenAI-compatible vLLM server for CDR-Bench evaluation.

Options:
  --model <path_or_name>           Required. HF model id or local model path.
  --served-model-name <name>       API-visible model name. Default: basename of --model
  --host <host>                    Default: 0.0.0.0
  --port <port>                    Default: 8000
  --api-key <key>                  Default: EMPTY
  --dtype <dtype>                  Default: auto
  --tensor-parallel-size <int>     Default: 1
  --gpu-memory-utilization <float> Default: 0.92
  --max-model-len <value>          Optional. Example: 32768 or 32k
  --trust-remote-code              Pass through to vLLM
  --help                           Show this help

Examples:
  ./scripts/serve_vllm_openai.sh \
    --model /models/Qwen2.5-7B-Instruct \
    --served-model-name qwen2.5-7b-instruct \
    --tensor-parallel-size 2 \
    --port 8000

  ./scripts/serve_vllm_openai.sh \
    --model meta-llama/Llama-3.1-8B-Instruct \
    --api-key EMPTY \
    -- --max-num-seqs 32
EOF
}

MODEL=""
SERVED_MODEL_NAME=""
HOST="0.0.0.0"
PORT="8000"
API_KEY="EMPTY"
DTYPE="auto"
TENSOR_PARALLEL_SIZE="1"
GPU_MEMORY_UTILIZATION="0.92"
MAX_MODEL_LEN=""
TRUST_REMOTE_CODE="false"
EXTRA_ARGS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --model)
      MODEL="$2"
      shift 2
      ;;
    --served-model-name)
      SERVED_MODEL_NAME="$2"
      shift 2
      ;;
    --host)
      HOST="$2"
      shift 2
      ;;
    --port)
      PORT="$2"
      shift 2
      ;;
    --api-key)
      API_KEY="$2"
      shift 2
      ;;
    --dtype)
      DTYPE="$2"
      shift 2
      ;;
    --tensor-parallel-size)
      TENSOR_PARALLEL_SIZE="$2"
      shift 2
      ;;
    --gpu-memory-utilization)
      GPU_MEMORY_UTILIZATION="$2"
      shift 2
      ;;
    --max-model-len)
      MAX_MODEL_LEN="$2"
      shift 2
      ;;
    --trust-remote-code)
      TRUST_REMOTE_CODE="true"
      shift 1
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    --)
      shift
      EXTRA_ARGS=("$@")
      break
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

if [[ -z "$SERVED_MODEL_NAME" ]]; then
  SERVED_MODEL_NAME="$(basename "$MODEL")"
fi

if ! command -v vllm >/dev/null 2>&1; then
  echo "vllm command not found. Install vLLM first." >&2
  exit 1
fi

cmd=(
  vllm serve "$MODEL"
  --host "$HOST"
  --port "$PORT"
  --api-key "$API_KEY"
  --dtype "$DTYPE"
  --served-model-name "$SERVED_MODEL_NAME"
  --tensor-parallel-size "$TENSOR_PARALLEL_SIZE"
  --gpu-memory-utilization "$GPU_MEMORY_UTILIZATION"
  --generation-config vllm
)

if [[ -n "$MAX_MODEL_LEN" ]]; then
  cmd+=(--max-model-len "$MAX_MODEL_LEN")
fi
if [[ "$TRUST_REMOTE_CODE" == "true" ]]; then
  cmd+=(--trust-remote-code)
fi
if [[ ${#EXTRA_ARGS[@]} -gt 0 ]]; then
  cmd+=("${EXTRA_ARGS[@]}")
fi

printf 'Launching vLLM server for model=%s on %s:%s\n' "$SERVED_MODEL_NAME" "$HOST" "$PORT"
printf 'API base URL: http://%s:%s/v1\n' "$HOST" "$PORT"
exec "${cmd[@]}"
