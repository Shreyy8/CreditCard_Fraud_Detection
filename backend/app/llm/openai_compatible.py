"""OpenAI-compatible adapter for Grok, OpenAI, and compatible endpoints."""

from __future__ import annotations

import json
import time
from typing import Any

from ..config import Settings
from .base import LLMGeneration


class OpenAICompatibleProvider:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def generate_structured(
        self, *, system_prompt: str, user_prompt: str
    ) -> LLMGeneration:
        import openai

        started = time.monotonic()
        api_key = self.settings.llm_api_key
        used_backup = False

        async def request(key: str):
            client_kwargs: dict[str, Any] = {
                "api_key": key,
                "timeout": self.settings.llm_timeout_s,
            }
            if self.settings.llm_base_url:
                client_kwargs["base_url"] = self.settings.llm_base_url
            client = openai.AsyncOpenAI(**client_kwargs)
            return await client.chat.completions.create(
                model=self.settings.llm_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
                max_tokens=1200,
            )

        try:
            response = await request(api_key)
        except Exception as exc:
            status_code = getattr(exc, "status_code", None)
            if status_code not in {401, 429} or not self.settings.llm_backup_api_key:
                raise
            used_backup = True
            response = await request(self.settings.llm_backup_api_key)
        content = response.choices[0].message.content or ""
        try:
            data = json.loads(content, strict=False)
        except json.JSONDecodeError:
            start, end = content.find("{"), content.rfind("}")
            if start < 0 or end <= start:
                raise
            data = json.loads(content[start:end + 1], strict=False)
        if not isinstance(data, dict):
            raise ValueError("LLM response JSON must be an object")
        usage = response.usage
        return LLMGeneration(
            data=data,
            provider=self.settings.llm_provider,
            model=self.settings.llm_model,
            latency_ms=round((time.monotonic() - started) * 1000, 2),
            tokens=usage.total_tokens if usage else None,
            metadata={"api_calls": 2 if used_backup else 1, "backup_used": used_backup},
        )