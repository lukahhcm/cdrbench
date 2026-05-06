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
import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EVAL_PATH = REPO_ROOT / "data" / "benchmark" / "main" / "main.jsonl"
DEFAULT_PROMPT_CONFIG = REPO_ROOT / "configs" / "recipe_prompting.yaml"

OVERSEAS_URL = "https://eval.dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
DOMESTIC_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"

DEFAULT_MAX_TOKENS = 1024


@dataclass
class ModelConfig:
    model_name: str
    endpoint: str
    input_field: str = "messages"
    need_max_tokens: bool = False
    temperature: float = 0.0
    top_p: float | None = None
    enable_thinking: bool | None = None
    vendor: str = ""
    note: str = ""


ALL_MODELS: list[ModelConfig] = [
    ModelConfig("openai.gpt-5.4-2026-03-05", "overseas", vendor="OpenAI"),
    ModelConfig("vertex_ai.claude-sonnet-4-6", "overseas", need_max_tokens=True, vendor="Claude"),
    ModelConfig("vertex_ai.claude-opus-4-5-20251101", "overseas", need_max_tokens=True, vendor="Claude"),
    ModelConfig("grok-4-1-fast-reasoning", "overseas", vendor="Grok"),
    ModelConfig("z_ai.glm-5", "overseas", vendor="GLM"),
    ModelConfig("moonshot.kimi-k2.5", "overseas", temperature=1.0, top_p=0.95, vendor="Kimi"),
    ModelConfig("qwen3.6-max-preview", "domestic", enable_thinking=False, vendor="Qwen"),
    ModelConfig("qwen3.6-plus", "domestic", enable_thinking=False, vendor="Qwen"),
    ModelConfig("deepseek-v4-pro", "domestic", vendor="DeepSeek"),
    ModelConfig("deepseek-v4-flash", "domestic", vendor="DeepSeek"),
    ModelConfig("kimi-k2.6", "domestic", temperature=1.0, top_p=0.95, vendor="Kimi"),
    ModelConfig("glm-5.1", "domestic", vendor="GLM"),
]


def build_model_lookup() -> dict[str, ModelConfig]:
    return {item.model_name: item for item in ALL_MODELS}


def build_payload(cfg: ModelConfig, prompt_bundle: dict[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {"model": cfg.model_name}
    system_prompt = str(prompt_bundle.get("system_prompt") or "")
    user_prompt = str(prompt_bundle.get("user_prompt") or "")
    combined_prompt = str(prompt_bundle.get("combined_prompt") or user_prompt)

    if cfg.input_field == "messages":
        payload["messages"] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
    elif cfg.input_field == "input":
        payload["input"] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
    elif cfg.input_field == "contents":
        payload["contents"] = [{"role": "user", "parts": [{"text": combined_prompt}]}]

    if cfg.need_max_tokens:
        payload["max_tokens"] = DEFAULT_MAX_TOKENS
    payload["temperature"] = cfg.temperature
    if cfg.top_p is not None and cfg.top_p > 0:
        payload["top_p"] = cfg.top_p
    if cfg.enable_thinking is not None:
        payload["enable_thinking"] = cfg.enable_thinking

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


def load_prompt_config(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle)
    return payload if isinstance(payload, dict) else {}


def default_system_prompt(prompt_cfg: dict[str, Any]) -> str:
    prompt_styles = prompt_cfg.get("prompt_styles") or {}
    style_cfg = prompt_styles.get("user_natural_v1") or {}
    prompt = style_cfg.get("system_prompt") if isinstance(style_cfg, dict) else None
    if isinstance(prompt, str) and prompt.strip():
        return prompt.strip()
    return (
        "You are a careful data refinement engine. "
        "Follow the user request exactly and in order. "
        "Return only the required tagged output."
    )


def tagged_output_hint(prompt_cfg: dict[str, Any]) -> str:
    prompt_styles = prompt_cfg.get("prompt_styles") or {}
    style_cfg = prompt_styles.get("user_natural_v1") or {}
    output_contract = style_cfg.get("output_contract") if isinstance(style_cfg, dict) else {}
    hint = output_contract.get("tagged_output_hint") if isinstance(output_contract, dict) else None
    if isinstance(hint, str) and hint.strip():
        return hint.strip()
    return "<status>KEEP</status><clean_text>...</clean_text> or <status>DROP</status><clean_text>...</clean_text>"


def select_prompt_variant(row: dict[str, Any], prompt_variant_index: int) -> dict[str, Any]:
    prompt_variants = row.get("prompt_variants")
    if isinstance(prompt_variants, list) and prompt_variants:
        selected = prompt_variants[prompt_variant_index]
        if isinstance(selected, dict):
            return selected
    user_requirement = row.get("user_requirement")
    if isinstance(user_requirement, str) and user_requirement.strip():
        return {
            "style_id": str(row.get("style_id") or "single_prompt"),
            "style_label": str(row.get("style_label") or "Single Prompt"),
            "user_requirement": user_requirement.strip(),
        }
    raise RuntimeError("第一条 benchmark 数据没有可用的 prompt variant。")


def render_user_prompt(row: dict[str, Any], user_requirement: str, output_hint: str) -> str:
    return (
        f"Task:\n{user_requirement}\n\n"
        "Raw input text:\n"
        "<input>\n"
        f"{str(row.get('input_text', ''))}\n"
        "</input>\n\n"
        "Return tagged output only.\n"
        f"Use exactly this format: {output_hint}\n"
        "Rules:\n"
        "- status must be KEEP or DROP inside <status>...</status>.\n"
        "- Put the output text inside <clean_text>...</clean_text>.\n"
        "- If status is KEEP, clean_text must be the final refined text.\n"
        "- If status is DROP, clean_text must be the text state at the point where the sample is rejected.\n"
        "- Preserve backslashes exactly as plain text; do not JSON-escape them.\n"
        "- Do not output markdown, code fences, or explanations.\n"
    )


def final_user_prompt(row: dict[str, Any], user_requirement: str, output_hint: str, model_name: str) -> str:
    return render_user_prompt(row, user_requirement, output_hint)


def read_first_eval_row(eval_path: Path) -> dict[str, Any]:
    with eval_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                return json.loads(line)
    raise RuntimeError(f"评测文件为空: {eval_path}")


def resolve_prompt(
    eval_path_arg: str | None,
    prompt_config_arg: str | None,
    prompt_variant_index: int,
    model_name: str,
) -> tuple[dict[str, str], str]:
    eval_path = Path(eval_path_arg or DEFAULT_EVAL_PATH).resolve()
    if not eval_path.is_file():
        raise FileNotFoundError(
            f"benchmark main track 文件不存在: {eval_path}\n"
            "请通过 --eval-path 指定 main.jsonl。"
        )
    prompt_config_path = Path(prompt_config_arg or DEFAULT_PROMPT_CONFIG).resolve()
    if not prompt_config_path.is_file():
        raise FileNotFoundError(f"prompt 配置文件不存在: {prompt_config_path}")

    row = read_first_eval_row(eval_path)
    prompt_cfg = load_prompt_config(prompt_config_path)
    variant = select_prompt_variant(row, prompt_variant_index)
    user_requirement = str(variant.get("user_requirement") or "").strip()
    output_hint = tagged_output_hint(prompt_cfg)
    system_prompt = default_system_prompt(prompt_cfg)
    user_prompt = final_user_prompt(row, user_requirement, output_hint, model_name)
    return {
        "system_prompt": system_prompt,
        "user_prompt": user_prompt,
        "combined_prompt": f"{system_prompt}\n\n{user_prompt}",
    }, str(eval_path)


def test_model(api_key: str, cfg: ModelConfig, prompt_bundle: dict[str, Any], timeout: int = 120) -> dict[str, Any]:
    payload = build_payload(cfg, prompt_bundle)
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
            "request_flags": {
                "enable_thinking": cfg.enable_thinking,
            },
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
            "request_flags": {
                "enable_thinking": cfg.enable_thinking,
            },
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
            "request_flags": {
                "enable_thinking": cfg.enable_thinking,
            },
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
    parser.add_argument("--prompt-config", default=str(DEFAULT_PROMPT_CONFIG), help="benchmark prompt 配置")
    parser.add_argument("--prompt-variant-index", type=int, default=0, help="使用第几个 prompt variant")
    parser.add_argument("--timeout", type=int, default=120, help="请求超时时间（秒）")
    parser.add_argument("--output", default=None, help="将结果保存到 JSON 文件")
    args = parser.parse_args()

    lookup = build_model_lookup()
    results: list[dict[str, Any]] = []
    total = len(args.models)

    for index, model_name in enumerate(args.models, start=1):
        cfg = lookup.get(model_name)
        if cfg is None:
            cfg = ModelConfig(model_name, "overseas", vendor="Unknown", note="不在预定义列表中")
        prompt_bundle, prompt_source = resolve_prompt(args.eval_path, args.prompt_config, args.prompt_variant_index, cfg.model_name)

        endpoint_label = "海外" if cfg.endpoint == "overseas" else "国内"
        print(f"[{index}/{total}] 测试 {model_name} ({endpoint_label}/{cfg.vendor}) ...", end=" ", flush=True)

        result = test_model(args.api_key, cfg, prompt_bundle, args.timeout)
        results.append(result)

        if result["success"]:
            print(f"✅ 成功 ({result['elapsed']}s)")
            if cfg.enable_thinking is not None:
                print(f"    请求参数: enable_thinking={str(cfg.enable_thinking).lower()}")
            preview = (result["response"] or "")[:120]
            print(f"    回复: {preview}")
            if result.get("raw_keys"):
                print(f"    返回字段: {result['raw_keys']}")
        else:
            print("❌ 失败")
            if cfg.enable_thinking is not None:
                print(f"    请求参数: enable_thinking={str(cfg.enable_thinking).lower()}")
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
