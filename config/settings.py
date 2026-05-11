"""
JARVIS V300 OMNIPOTENCE - Central Configuration
================================================
All tunable parameters for every subsystem live here so the rest of the codebase
can stay clean. Edit values; do not hard-code them elsewhere.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT_DIR: Path = Path(__file__).resolve().parent.parent
APPS_DIR: Path = ROOT_DIR / "apps"
LOGS_DIR: Path = ROOT_DIR / "logs"
DATA_DIR: Path = ROOT_DIR / "data"
STATE_DIR: Path = DATA_DIR / "state"
RESEARCH_DIR: Path = DATA_DIR / "research"
SCREENSHOT_DIR: Path = DATA_DIR / "screenshots"

for _p in (APPS_DIR, LOGS_DIR, DATA_DIR, STATE_DIR, RESEARCH_DIR, SCREENSHOT_DIR):
    _p.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Identity
# ---------------------------------------------------------------------------
OWNER_TITLE: str = os.getenv("JARVIS_OWNER_TITLE", "Sir")
ASSISTANT_NAME: str = "J.A.R.V.I.S."
VERSION: str = "V300-OMNIPOTENCE"


# ---------------------------------------------------------------------------
# Trading configuration (MetaTrader 5)
# ---------------------------------------------------------------------------
@dataclass
class TradingConfig:
    # Symbol selection - low-spread, high-liquidity instruments suited for M1 scalping.
    symbols: List[str] = field(default_factory=lambda: ["EURUSD", "XAUUSD", "GBPUSD"])
    timeframe_minutes: int = 1            # M1 scalping
    htf_minutes: int = 15                 # HTF bias filter
    history_bars: int = 600

    # Capital plan: 10 EUR -> 100 EUR
    start_balance: float = 10.0
    target_balance: float = 100.0

    # Risk
    risk_per_trade: float = 0.05          # 5% per trade (aggressive scalping plan)
    max_daily_dd: float = 0.20            # stop new trades at -20% daily drawdown
    max_concurrent: int = 1               # one position at a time

    # Stops / TP
    sl_atr_mult: float = 1.2
    tp_rr: float = 2.0                    # min RR
    trail_atr_mult: float = 0.8           # ATR multiple for trailing
    trail_activate_rr: float = 1.0        # start trailing after +1R

    # Confluence
    min_confluence: float = 0.90          # 90%+ confluence required

    # News protection
    news_blackout_minutes: int = 15       # block trading +/- N minutes around high impact news

    # Engine
    poll_interval_sec: float = 2.0
    magic_number: int = 30070
    slippage_points: int = 20
    comment: str = "JARVIS_V300_SMC"


TRADING = TradingConfig()


# ---------------------------------------------------------------------------
# Voice configuration
# ---------------------------------------------------------------------------
@dataclass
class VoiceConfig:
    enabled: bool = True
    language: str = "de-DE"
    rate: int = 185
    volume: float = 1.0
    wake_words: List[str] = field(default_factory=lambda: ["jarvis", "jarwis", "jarvi"])


VOICE = VoiceConfig()


# ---------------------------------------------------------------------------
# Vision / OS control
# ---------------------------------------------------------------------------
@dataclass
class VisionConfig:
    monitor_index: int = 1                # primary monitor for mss
    scan_interval_sec: float = 0.25
    bezier_min_duration: float = 0.18
    bezier_max_duration: float = 0.55
    pyautogui_failsafe: bool = True


VISION = VisionConfig()


# ---------------------------------------------------------------------------
# Ghost / Security
# ---------------------------------------------------------------------------
@dataclass
class GhostConfig:
    headless: bool = True
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
    news_sources: List[str] = field(default_factory=lambda: [
        "https://www.forexfactory.com/calendar",
        "https://www.investing.com/economic-calendar/",
    ])
    request_timeout_ms: int = 25_000


GHOST = GhostConfig()


# ---------------------------------------------------------------------------
# Master brain
# ---------------------------------------------------------------------------
@dataclass
class BrainConfig:
    tick_interval_sec: float = 1.0
    event_log: Path = LOGS_DIR / "events.log"
    audit_log: Path = LOGS_DIR / "audit.log"
    trade_log: Path = LOGS_DIR / "trades.log"
    equity_log: Path = LOGS_DIR / "equity.csv"
    signals_log: Path = LOGS_DIR / "signals.csv"


BRAIN = BrainConfig()
