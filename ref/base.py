#!/usr/bin/env python3
"""
推理基类：定义统一接口和数据结构。
所有推理后端都继承 BaseInfer，实现 infer_one 即可。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, List, Optional

import logging

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

from tqdm import tqdm

@dataclass
class InferResult:
    """
    单条样本的推理结果。
    - num_runs=1 时：contents 长度为1，用 contents[0] 取结果
    - num_runs>1 时：contents 长度为k，调用方自行选最优
    - error 非None 表示推理失败，contents 为空列表
    """
    contents: List[str]           # 模型输出列表（长度 = num_runs）
    error:    Optional[str] = None       # 失败原因，成功时为 None
    raw:      Any           = field(default=None, repr=False)  # 原始 response，调试用

    @property
    def text(self) -> str:
        """取第一条输出，失败时返回空字符串。"""
        return self.contents[0] if self.contents else ""

    @property
    def ok(self) -> bool:
        return self.error is None


class BaseInfer(ABC):
    """
    推理基类。子类只需实现 _call_once（单次 API 调用）。

    统一接口：
        infer_one(messages)          -> InferResult   # 单条
        infer(messages_list)         -> List[InferResult]  # 批量（线程池）
    """

    def __init__(
        self,
        model:       str,
        concurrency: int   = 8,
        max_tokens:  int   = 16392,
        temperature: float = 0.0,
        num_runs:    int   = 1,
    ) -> None:
        self.model       = model
        self.concurrency = concurrency
        self.max_tokens  = max_tokens
        self.temperature = temperature
        self.num_runs    = num_runs

    @abstractmethod
    def _call_once(self, messages: List[dict]) -> str:
        """
        单次模型调用，返回文本。失败时抛异常，由上层捕获。
        子类实现这一个方法即可，不需要关心重试和并发。
        """

    def infer_one(self, messages: List[dict]) -> InferResult:
        """
        对单条 messages 执行 num_runs 次推理。
        任意一次失败则整条标记为 error（已成功的部分丢弃）。
        """
        if not messages:
            return InferResult(contents=[], error="empty messages")
        try:
            contents = [self._call_once(messages) for _ in range(self.num_runs)]
            return InferResult(contents=contents)
        except Exception as e:
            return InferResult(contents=[], error=str(e))

    def infer(self, messages_list: List[List[dict]]) -> List[InferResult]:
        """
        批量推理，内部用 ThreadPoolExecutor 并发。
        返回列表顺序与输入严格对应。
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed

        n = len(messages_list)
        results: List[Optional[InferResult]] = [None] * n

        with ThreadPoolExecutor(max_workers=self.concurrency) as pool:
            future_to_idx = {
                pool.submit(self.infer_one, messages_list[i]): i
                for i in range(n)
            }
            for future in tqdm(as_completed(future_to_idx), total=n, desc=f"infer [{self.model}]"):
                idx = future_to_idx[future]
                try:
                    results[idx] = future.result()
                except Exception as e:
                    results[idx] = InferResult(contents=[], error=str(e))

        return results  # type: ignore[return-value]
