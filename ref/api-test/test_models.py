#!/usr/bin/env python3
"""模型可用性测试脚本
支持双 endpoint 路由：
  - 海外模型 → https://eval.dashscope.aliyuncs.com/compatible-mode/v1/chat/completions
  - 国内模型 → https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions
"""

import argparse
import json
import sys
import time
from dataclasses import dataclass, field

import requests

# ── Endpoint ──────────────────────────────────────────────
OVERSEAS_URL = "https://eval.dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
DOMESTIC_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"

DEFAULT_PROMPT = "你好，请用一句话介绍你自己。"
DEFAULT_MAX_TOKENS = 1024


@dataclass
class ModelConfig:
    """单个模型的配置"""
    model_name: str
    endpoint: str               # "overseas" | "domestic"
    input_field: str = "messages"   # messages / input / contents
    need_max_tokens: bool = False
    vendor: str = ""
    note: str = ""


# ── 全部模型配置 ──────────────────────────────────────────
ALL_MODELS: list[ModelConfig] = [
    # ==================== 海外模型 (eval.dashscope) ====================
    # OpenAI
    ModelConfig("openai.gpt-5.4-2026-03-05",       "overseas", vendor="OpenAI"),
    ModelConfig("openai.gpt-5.4-pro-2026-03-05",    "overseas", input_field="input", need_max_tokens=True, vendor="OpenAI"),
    # Claude
    ModelConfig("vertex_ai.claude-sonnet-4-6",       "overseas", need_max_tokens=True, vendor="Claude"),
    ModelConfig("vertex_ai.claude-opus-4-6",         "overseas", need_max_tokens=True, vendor="Claude"),
    ModelConfig("vertex_ai.claude-opus-4-5-20251101","overseas", need_max_tokens=True, vendor="Claude"),
    # Gemini
    ModelConfig("vertex_ai.gemini-3.1-pro-preview",  "overseas", input_field="contents", vendor="Gemini"),
    ModelConfig("vertex_ai.gemini-3-pro-preview",    "overseas", input_field="contents", vendor="Gemini"),
    ModelConfig("ai_studio.gemini-3-pro-image-preview", "overseas", input_field="contents", vendor="Gemini"),
    # Grok
    ModelConfig("grok-4-1-fast-reasoning",           "overseas", vendor="Grok"),

    # ==================== 国内模型 (dashscope) =========================
    # GLM（文档中列在 eval 平台，但属于国内厂商，两个 endpoint 都试）
    ModelConfig("glm-4.7-inner",   "overseas", vendor="GLM", note="文档列在eval平台"),
    ModelConfig("glm-image",       "overseas", vendor="GLM", note="文档列在eval平台"),
    ModelConfig("z_ai.glm-5",      "overseas", vendor="GLM", note="文档列在eval平台"),
    # Kimi（文档列在 eval 平台）
    ModelConfig("moonshot.kimi-k2.5", "overseas", vendor="Kimi", note="文档列在eval平台"),

    # 新增国内模型 → 走 dashscope 原生 endpoint
    ModelConfig("qwen3.6-max-preview", "domestic", vendor="Qwen"),
    ModelConfig("qwen3.6-plus",        "domestic", vendor="Qwen"),
    ModelConfig("deepseek-v4-pro",     "domestic", vendor="DeepSeek"),
    ModelConfig("deepseek-v4-flash",   "domestic", vendor="DeepSeek"),
    ModelConfig("kimi-k2.6",           "domestic", vendor="Kimi"),
    ModelConfig("glm-5.1",             "domestic", vendor="GLM"),
    ModelConfig("minimax-m2.7",        "domestic", vendor="MiniMax"),
]


def build_model_lookup() -> dict[str, ModelConfig]:
    return {m.model_name: m for m in ALL_MODELS}


def build_payload(cfg: ModelConfig, prompt: str) -> dict:
    """根据模型配置构建请求 payload"""
    payload: dict = {"model": cfg.model_name}

    if cfg.input_field == "messages":
        payload["messages"] = [{"role": "user", "content": prompt}]
    elif cfg.input_field == "input":
        payload["input"] = [{"role": "user", "content": prompt}]
    elif cfg.input_field == "contents":
        payload["contents"] = [{"role": "user", "parts": [{"text": prompt}]}]

    if cfg.need_max_tokens:
        payload["max_tokens"] = DEFAULT_MAX_TOKENS

    return payload


def get_url(cfg: ModelConfig) -> str:
    return OVERSEAS_URL if cfg.endpoint == "overseas" else DOMESTIC_URL


def test_model(api_key: str, cfg: ModelConfig, prompt: str, timeout: int = 120) -> dict:
    """测试单个模型"""
    payload = build_payload(cfg, prompt)
    url = get_url(cfg)
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    start = time.time()
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
        elapsed = time.time() - start

        result = {
            "model": cfg.model_name,
            "vendor": cfg.vendor,
            "endpoint": cfg.endpoint,
            "url": url,
            "status_code": resp.status_code,
            "elapsed": round(elapsed, 2),
            "success": False,
            "response": None,
            "error": None,
        }

        if resp.status_code == 200:
            data = resp.json()
            content = extract_content(data)
            result["success"] = True
            result["response"] = content
            result["raw_keys"] = list(data.keys())  # 记录返回的顶层 key，方便排查
        else:
            result["error"] = resp.text

        return result

    except requests.exceptions.Timeout:
        return {
            "model": cfg.model_name,
            "vendor": cfg.vendor,
            "endpoint": cfg.endpoint,
            "url": url,
            "status_code": None,
            "elapsed": timeout,
            "success": False,
            "response": None,
            "error": f"请求超时（>{timeout}s）",
        }
    except Exception as e:
        return {
            "model": cfg.model_name,
            "vendor": cfg.vendor,
            "endpoint": cfg.endpoint,
            "url": url,
            "status_code": None,
            "elapsed": round(time.time() - start, 2),
            "success": False,
            "response": None,
            "error": str(e),
        }


def extract_content(data: dict) -> str:
    """从不同格式的响应中提取回复内容"""
    # 标准 OpenAI compatible 格式
    if "choices" in data and len(data["choices"]) > 0:
        choice = data["choices"][0]
        if "message" in choice:
            return choice["message"].get("content", "")

    # Claude 原生格式
    if "content" in data and isinstance(data["content"], list):
        parts = [p.get("text", "") for p in data["content"] if p.get("type") == "text"]
        return "".join(parts)

    # Gemini 原生格式
    if "candidates" in data and len(data["candidates"]) > 0:
        candidate = data["candidates"][0]
        if "content" in candidate and "parts" in candidate["content"]:
            parts = [p.get("text", "") for p in candidate["content"]["parts"]]
            return "".join(parts)

    # DashScope 原生格式
    if "output" in data:
        output = data["output"]
        if isinstance(output, dict):
            if "text" in output:
                return output["text"]
            if "choices" in output and len(output["choices"]) > 0:
                msg = output["choices"][0].get("message", {})
                return msg.get("content", "")

    return json.dumps(data, ensure_ascii=False)


def main():
    parser = argparse.ArgumentParser(description="测试模型可用性")
    parser.add_argument("--api-key", required=True, help="DashScope API Key")
    parser.add_argument("--models", required=True, nargs="+", help="要测试的模型名称列表")
    parser.add_argument("--prompt", default=DEFAULT_PROMPT, help="测试用的 prompt")
    parser.add_argument("--timeout", type=int, default=120, help="请求超时时间（秒）")
    parser.add_argument("--output", default=None, help="将结果保存到 JSON 文件")
    args = parser.parse_args()

    lookup = build_model_lookup()
    results = []
    total = len(args.models)

    for idx, model_name in enumerate(args.models, 1):
        cfg = lookup.get(model_name)
        if cfg is None:
            # 未知模型，使用默认配置尝试 overseas endpoint
            cfg = ModelConfig(model_name, "overseas", vendor="Unknown", note="不在预定义列表中")

        ep_label = "海外" if cfg.endpoint == "overseas" else "国内"
        print(f"[{idx}/{total}] 测试 {model_name} ({ep_label}/{cfg.vendor}) ...", end=" ", flush=True)

        result = test_model(args.api_key, cfg, args.prompt, args.timeout)
        results.append(result)

        if result["success"]:
            print(f"✅ 成功 ({result['elapsed']}s)")
            preview = (result["response"] or "")[:120]
            print(f"    回复: {preview}")
            if result.get("raw_keys"):
                print(f"    返回字段: {result['raw_keys']}")
        else:
            print(f"❌ 失败")
            err_preview = (result["error"] or "")[:200]
            print(f"    错误: {err_preview}")
        print()

    # 汇总
    success_count = sum(1 for r in results if r["success"])
    print("=" * 60)
    print(f"汇总: {success_count}/{total} 个模型可用")
    print("-" * 60)
    for r in results:
        mark = "✅" if r["success"] else "❌"
        ep = r.get("endpoint", "?")
        vendor = r.get("vendor", "?")
        print(f"  {mark} [{ep:8s}/{vendor:8s}] {r['model']}")
        if r.get("note"):
            print(f"      备注: {r['note']}")

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"\n结果已保存到 {args.output}")

    sys.exit(0 if success_count == total else 1)


if __name__ == "__main__":
    main()
