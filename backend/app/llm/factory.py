"""Provider factory. Business logic depends on this boundary, not SDKs."""

from __future__ import annotations

from ..config import Settings, get_settings
from .openai_compatible import OpenAICompatibleProvider


def get_llm_provider(settings: Settings | None = None) -> OpenAICompatibleProvider:
    current = settings or get_settings()
    return OpenAICompatibleProvider(current)