"""Provider-agnostic LLM interfaces and adapters."""

from .base import LLMGeneration, LLMProvider
from .factory import get_llm_provider

__all__ = ["LLMGeneration", "LLMProvider", "get_llm_provider"]