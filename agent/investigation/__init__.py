"""Local investigation composition and answer validation."""

from .composer import compose_answer
from .validator import validate_answer

__all__ = ["compose_answer", "validate_answer"]