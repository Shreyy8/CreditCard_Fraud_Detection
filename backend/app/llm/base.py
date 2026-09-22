"""Stable provider contract for grounded investigation reasoning."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class LLMGeneration:
    data: dict[str, Any]
    provider: str
    model: str
    latency_ms: float
    tokens: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class LLMProvider(Protocol):
    async def generate_structured(
        self, *, system_prompt: str, user_prompt: str
    ) -> LLMGeneration:
        ...