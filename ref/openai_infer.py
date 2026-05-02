#!/usr/bin/env python3
"""
OpenAI-compatible 推理后端（统一实现 vLLM 本地服务和外部 API）。
"""

from __future__ import annotations

import os
import time
from typing import Any, Dict, List, Optional

from openai import OpenAI

from .base import BaseInfer, InferResult

import logging

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)


class OpenAIInfer(BaseInfer):
    """
    统一的 OpenAI-compatible 推理后端。
    vLLM 本地服务和外部 API 均走这一套逻辑，差异只在初始化参数。
    """

    def __init__(
        self,
        model:           str,
        api_base:        str,
        api_key:         str            = "EMPTY",
        concurrency:     int            = 8,
        max_tokens:      int            = 16392,
        temperature:     float          = 0.0,
        num_runs:        int            = 1,
        max_retries:     int            = 3,
        retry_delay:     float          = 1.0,    # 首次重试等待秒数，指数退避
        enable_thinking: bool           = False,
        extra_body:      Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            model       = model,
            concurrency = concurrency,
            max_tokens  = max_tokens,
            temperature = temperature,
            num_runs    = num_runs,
        )
        self.max_retries     = max_retries
        self.retry_delay     = retry_delay
        self.enable_thinking = enable_thinking

        # extra_body：调用方可完全自定义，默认只带 enable_thinking
        self._extra_body: Dict[str, Any] = (
            extra_body if extra_body is not None
            else {"chat_template_kwargs": {"enable_thinking": enable_thinking}}
        )

        self._client = OpenAI(api_key=api_key, base_url=api_base)

    # ── 核心单次调用 ───────────────────────────────────────────────────────────

    def _call_once(self, messages: List[dict]) -> str:
        """
        单次 API 调用，含 exponential backoff 重试。
        失败超过 max_retries 次后抛出最后一个异常。
        """
        last_exc: Exception = RuntimeError("no attempts made")
        delay = self.retry_delay

        for attempt in range(max(1, self.max_retries)):
            try:
                resp = self._client.chat.completions.create(
                    model      = self.model,
                    messages   = messages,
                    temperature= self.temperature,
                    max_tokens = self.max_tokens,
                    stream     = False,
                    extra_body = self._extra_body,
                )
                return resp.choices[0].message.content or ""
            except Exception as e:
                last_exc = e
                if attempt < self.max_retries - 1:
                    time.sleep(delay)
                    delay *= 2      # 指数退避

        raise last_exc

    # ── 便捷属性 ───────────────────────────────────────────────────────────────

    def __repr__(self) -> str:
        return (
            f"OpenAIInfer(model={self.model!r}, "
            f"concurrency={self.concurrency}, "
            f"num_runs={self.num_runs}, "
            f"enable_thinking={self.enable_thinking})"
        )


# ── 工厂函数 ───────────────────────────────────────────────────────────────────

def make_vllm_infer(
    model:           str,
    api_base:        str   = "http://127.0.0.1:8901/v1",
    concurrency:     int   = 128,
    max_tokens:      int   = 16392,
    temperature:     float = 0.0,
    num_runs:        int   = 1,
    enable_thinking: bool  = False,
) -> OpenAIInfer:
    """
    构造面向本地 vLLM 服务的推理实例。
    """
    return OpenAIInfer(
        model           = model,
        api_base        = api_base,
        api_key         = "EMPTY",
        concurrency     = concurrency,
        max_tokens      = max_tokens,
        temperature     = temperature,
        num_runs        = num_runs,
        max_retries     = 2,
        retry_delay     = 0.5,
        enable_thinking = enable_thinking,
    )


def make_api_infer(
    model:       str,
    api_base:    str   = "http://123.57.212.178:3333/v1",
    api_key:     str   = "",
    concurrency: int   = 8,
    max_tokens:  int   = 16392,
    temperature: float = 0.0,
    num_runs:    int   = 1,
) -> OpenAIInfer:
    """
    构造面向外部 API（GPT / DashScope 等）的推理实例。
    """
    resolved_key = api_key or os.getenv("DASHSCOPE_API_KEY", "EMPTY")
    return OpenAIInfer(
        model           = model,
        api_base        = api_base,
        api_key         = resolved_key,
        concurrency     = concurrency,
        max_tokens      = max_tokens,
        temperature     = temperature,
        num_runs        = num_runs,
        max_retries     = 3,
        retry_delay     = 1.0,
        enable_thinking = False,
    )
