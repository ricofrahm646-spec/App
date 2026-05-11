"""Shared configuration — override via environment variables or .env."""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent
APPS_DIR = ROOT / "apps"
LOGS_DIR = ROOT / "logs"
DATA_DIR = ROOT / "data"
NEWS_CACHE = DATA_DIR / "news_cache"
TEMPLATES_DIR = DATA_DIR / "templates"

for d in (APPS_DIR, LOGS_DIR, DATA_DIR, NEWS_CACHE, TEMPLATES_DIR):
    d.mkdir(parents=True, exist_ok=True)

# Trading
MT5_LOGIN = int(os.getenv("MT5_LOGIN", "0") or 0)
MT5_PASSWORD = os.getenv("MT5_PASSWORD", "")
MT5_SERVER = os.getenv("MT5_SERVER", "")
MT5_SYMBOL = os.getenv("MT5_SYMBOL", "EURUSD")
MT5_MAGIC = int(os.getenv("MT5_MAGIC", "90001") or 90001)
CONFLUENCE_MIN = float(os.getenv("CONFLUENCE_MIN", "0.9") or 0.9)
RISK_PCT = float(os.getenv("RISK_PCT", "0.5") or 0.5)
# Comma-separated UTC hours (0–23) to skip new entries, e.g. "14,15" — empty disables.
NEWS_SKIP_HOURS = os.getenv("NEWS_SKIP_HOURS", "")

# Research URLs (public pages only — respect robots.txt & site ToS)
RESEARCH_URLS = [
    u.strip()
    for u in os.getenv(
        "RESEARCH_URLS",
        "https://www.ecb.europa.eu/press/pr/date/2025/html/index.en.html",
    ).split(",")
    if u.strip()
]

# Voice
JARVIS_NAME = os.getenv("JARVIS_NAME", "Sir")
