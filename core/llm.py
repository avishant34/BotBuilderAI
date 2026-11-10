"""
Unified LLM client with retries, JSON repair, and metrics.
Supports OpenAI-compatible APIs (OpenAI, xAI, DeepSeek).
"""
from __future__ import annotations

import json
import re
import time
from typing import Any, Dict, List, Optional

from loguru import logger
from openai import AsyncOpenAI
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from core.config import get_settings
from core.exceptions import LLMError
from core.metrics import metrics


def _repair_json(raw: str) -> str:
    """Best-effort cleanup of common LLM JSON mistakes."""
    text = raw.strip()
    # strip markdown fences
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    # extract first {...} block if extra prose
    if not text.startswith("{"):
        m = re.search(r"\{[\s\S]*\}", text)
        if m:
            text = m.group(0)
    return text.strip()


class LLMClient:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._client: Optional[AsyncOpenAI] = None

    @property
    def client(self) -> AsyncOpenAI:
        if self._client is None:
            base_url = self.settings.LLM_BASE_URL
            if not base_url:
                provider = self.settings.LLM_PROVIDER.lower()
                if provider == "xai":
                    base_url = "https://api.x.ai/v1"
                elif provider == "deepseek":
                    base_url = "https://api.deepseek.com"
                else:
                    base_url = "https://api.openai.com/v1"
            self._client = AsyncOpenAI(
                api_key=self.settings.LLM_API_KEY,
                base_url=base_url,
                timeout=180.0,
                max_retries=0,  # we handle retries ourselves
            )
        return self._client

    @retry(
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=1.5, min=2, max=30),
        retry=retry_if_exception_type((LLMError, TimeoutError, ConnectionError)),
        reraise=True,
    )
    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        response_format: Optional[Dict[str, Any]] = None,
    ) -> str:
        t0 = time.perf_counter()
        kwargs: Dict[str, Any] = {
            "model": self.settings.LLM_MODEL,
            "messages": messages,
            "temperature": temperature if temperature is not None else self.settings.LLM_TEMPERATURE,
            "max_tokens": max_tokens or self.settings.LLM_MAX_TOKENS,
        }
        if response_format:
            kwargs["response_format"] = response_format

        try:
            resp = await self.client.chat.completions.create(**kwargs)
            content = (resp.choices[0].message.content or "").strip()
            metrics.timing("llm.chat_ms", (time.perf_counter() - t0) * 1000)
            metrics.incr("llm.chat_ok")
            return content
        except Exception as e:
            metrics.error("llm.chat", str(e))
            logger.error(f"LLM chat error: {e}")
            raise LLMError(str(e)) from e

    async def chat_json(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Force JSON; repair and parse with one recovery attempt."""
        content = await self.chat(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
        )
        try:
            return json.loads(_repair_json(content))
        except json.JSONDecodeError:
            logger.warning("JSON parse failed, asking model to repair")
            metrics.incr("llm.json_repair")
            repair_messages = messages + [
                {"role": "assistant", "content": content},
                {
                    "role": "user",
                    "content": (
                        "Your previous reply was not valid JSON. "
                        "Reply with ONLY a valid JSON object, no markdown, no commentary."
                    ),
                },
            ]
            fixed = await self.chat(
                messages=repair_messages,
                temperature=0,
                max_tokens=max_tokens,
                response_format={"type": "json_object"},
            )
            try:
                return json.loads(_repair_json(fixed))
            except json.JSONDecodeError as e:
                metrics.error("llm.json", str(e))
                raise LLMError(f"Invalid JSON from LLM after repair: {e}") from e


llm_client = LLMClient()
