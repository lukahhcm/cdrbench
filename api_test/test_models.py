#!/usr/bin/env python3
"""模型可用性测试脚本
请求方式与 api_test/ref/test_models.py 保持一致：
  - 海外模型 → https://eval.dashscope.aliyuncs.com/compatible-mode/v1/chat/completions
  - 国内模型 → https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions

只保留在参考结果中已经验证成功、并且用于 benchmark infer 的模型。
测试 prompt 来自 benchmark main track 的第一条数据。
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EVAL_PATH = REPO_ROOT / "data" / "benchmark" / "main" / "main.jsonl"

OVERSEAS_URL = "https://eval.dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
DOMESTIC_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"

DEFAULT_MAX_TOKENS = 1024


@dataclass
class ModelConfig:
    model_name: str
    endpoint: str
    input_field: str = "messages"
    need_max_tokens: bool = False
    vendor: str = ""
    note: str = ""


ALL_MODELS: list[ModelConfig] = [
    ModelConfig("openai.gpt-5.4-2026-03-05", "overseas", vendor="OpenAI"),
    ModelConfig("vertex_ai.claude-sonnet-4-6", "overseas", need_max_tokens=True, vendor="Claude"),
    ModelConfig("vertex_ai.claude-opus-4-5-20251101", "overseas", need_max_tokens=True, vendor="Claude"),
    ModelConfig("grok-4-1-fast-reasoning", "overseas", vendor="Grok"),
    ModelConfig("z_ai.glm-5", "overseas", vendor="GLM"),
    ModelConfig("moonshot.kimi-k2.5", "overseas", vendor="Kimi"),
    ModelConfig("qwen3.6-max-preview", "domestic", vendor="Qwen"),
    ModelConfig("qwen3.6-plus", "domestic", vendor="Qwen"),
    ModelConfig("deepseek-v4-pro", "domestic", vendor="DeepSeek"),
    ModelConfig("deepseek-v4-flash", "domestic", vendor="DeepSeek"),
    ModelConfig("kimi-k2.6", "domestic", vendor="Kimi"),
    ModelConfig("glm-5.1", "domestic", vendor="GLM"),
]


def build_model_lookup() -> dict[str, ModelConfig]:
    return {item.model_name: item for item in ALL_MODELS}


def build_payload(cfg: ModelConfig, prompt: str) -> dict[str, Any]:
    payload: dict[str, Any] = {"model": cfg.model_name}

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


def extract_content(data: dict[str, Any]) -> str:
    if "choices" in data and len(data["choices"]) > 0:
        choice = data["choices"][0]
        if "message" in choice:
            return choice["message"].get("content", "")

    if "content" in data and isinstance(data["content"], list):
        parts = [part.get("text", "") for part in data["content"] if part.get("type") == "text"]
        return "".join(parts)

    if "candidates" in data and len(data["candidates"]) > 0:
        candidate = data["candidates"][0]
        if "content" in candidate and "parts" in candidate["content"]:
            parts = [part.get("text", "") for part in candidate["content"]["parts"]]
            return "".join(parts)

    if "output" in data:
        output = data["output"]
        if isinstance(output, dict):
            if "text" in output:
                return output["text"]
            if "choices" in output and len(output["choices"]) > 0:
                message = output["choices"][0].get("message", {})
                return message.get("content", "")

    return json.dumps(data, ensure_ascii=False)


def read_prompt_from_eval(eval_path: Path) -> str:
    with eval_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            for key in ("input_text", "text", "user_requirement", "reference_text"):
                value = row.get(key)
                if isinstance(value, str) and value.strip():
                    return value
            return json.dumps(row, ensure_ascii=False)
    raise RuntimeError(f"评测文件为空: {eval_path}")


def resolve_prompt(eval_path_arg: str | None) -> tuple[str, str]:
    eval_path = Path(eval_path_arg or DEFAULT_EVAL_PATH).resolve()
    if not eval_path.is_file():
        raise FileNotFoundError(
            f"benchmark main track 文件不存在: {eval_path}\n"
            "请通过 --eval-path 指定 main.jsonl。"
        )
    return read_prompt_from_eval(eval_path), str(eval_path)


def test_model(api_key: str, cfg: ModelConfig, prompt: str, timeout: int = 120) -> dict[str, Any]:
    payload = build_payload(cfg, prompt)
    url = get_url(cfg)
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    start = time.time()
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=timeout)
        elapsed = time.time() - start

        result = {
            "model": cfg.model_name,
            "vendor": cfg.vendor,
            "endpoint": cfg.endpoint,
            "url": url,
            "status_code": response.status_code,
            "elapsed": round(elapsed, 2),
            "success": False,
            "response": None,
            "error": None,
        }

        if response.status_code == 200:
            data = response.json()
            result["success"] = True
            result["response"] = extract_content(data)
            result["raw_keys"] = list(data.keys())
        else:
            result["error"] = response.text

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
    except Exception as exc:
        return {
            "model": cfg.model_name,
            "vendor": cfg.vendor,
            "endpoint": cfg.endpoint,
            "url": url,
            "status_code": None,
            "elapsed": round(time.time() - start, 2),
            "success": False,
            "response": None,
            "error": str(exc),
        }


def main() -> int:
    parser = argparse.ArgumentParser(description="测试模型可用性")
    parser.add_argument("--api-key", required=True, help="DashScope API Key")
    parser.add_argument("--models", required=True, nargs="+", help="要测试的模型名称列表")
    parser.add_argument("--eval-path", default=str(DEFAULT_EVAL_PATH), help="main track JSONL；取第一条数据作为 prompt")
    parser.add_argument("--timeout", type=int, default=120, help="请求超时时间（秒）")
    parser.add_argument("--output", default=None, help="将结果保存到 JSON 文件")
    args = parser.parse_args()

    prompt, prompt_source = resolve_prompt(args.eval_path)

    lookup = build_model_lookup()
    results: list[dict[str, Any]] = []
    total = len(args.models)

    for index, model_name in enumerate(args.models, start=1):
        cfg = lookup.get(model_name)
        if cfg is None:
            cfg = ModelConfig(model_name, "overseas", vendor="Unknown", note="不在预定义列表中")

        endpoint_label = "海外" if cfg.endpoint == "overseas" else "国内"
        print(f"[{index}/{total}] 测试 {model_name} ({endpoint_label}/{cfg.vendor}) ...", end=" ", flush=True)

        result = test_model(args.api_key, cfg, prompt, args.timeout)
        results.append(result)

        if result["success"]:
            print(f"✅ 成功 ({result['elapsed']}s)")
            preview = (result["response"] or "")[:120]
            print(f"    回复: {preview}")
            if result.get("raw_keys"):
                print(f"    返回字段: {result['raw_keys']}")
        else:
            print("❌ 失败")
            error_preview = (result["error"] or "")[:200]
            print(f"    错误: {error_preview}")
        print()

    success_count = sum(1 for item in results if item["success"])
    success_models = [item["model"] for item in results if item["success"]]
    failed_models = [item["model"] for item in results if not item["success"]]

    print("=" * 60)
    print(f"汇总: {success_count}/{total} 个模型可用")
    print("-" * 60)
    for item in results:
        mark = "✅" if item["success"] else "❌"
        endpoint = item.get("endpoint", "?")
        vendor = item.get("vendor", "?")
        print(f"  {mark} [{endpoint:8s}/{vendor:8s}] {item['model']}")
        if item.get("note"):
            print(f"      备注: {item['note']}")

    print("-" * 60)
    print("能跑的模型:")
    for model in success_models:
        print(f"  - {model}")
    print("不能跑的模型:")
    for model in failed_models:
        print(f"  - {model}")

    if args.output:
        output_path = Path(args.output).resolve()
        payload = {
            "prompt_source": prompt_source,
            "successful_models": success_models,
            "failed_models": failed_models,
            "results": results,
        }
        output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"\n结果已保存到 {output_path}")

    return 0 if success_count == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
