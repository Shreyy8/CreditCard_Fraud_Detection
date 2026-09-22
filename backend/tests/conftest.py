"""Pytest configuration — ensure the backend package is importable."""
import sys
from pathlib import Path

# Add backend/ to path so 'app' is importable
sys.path.insert(0, str(Path(__file__).parent.parent))
