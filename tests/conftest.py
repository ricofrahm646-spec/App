"""Pytest fixtures for JARVIS."""
import os
import sys
from pathlib import Path

# Ensure project root is importable
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Force mock mode + isolate from external services
os.environ.setdefault("MT5_MOCK", "true")
os.environ.setdefault("LLM_PROVIDER", "local")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
