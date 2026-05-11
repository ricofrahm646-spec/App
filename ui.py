"""
ui.py
=====
J.A.R.V.I.S. V300 - "War Room" Streamlit Dashboard.

Style: deep-black with neon-blue accents (cyan #00E5FF on #05070C). Live
panels for equity curve, agent signals, screen-vision feed, ghost research
and a live event log.

Run with:
    streamlit run ui.py
"""
from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path
from typing import List

import pandas as pd
import streamlit as st

from config import ASSISTANT_NAME, BRAIN, OWNER_TITLE, RESEARCH_DIR, SCREENSHOT_DIR, TRADING, VERSION
from core import bus

# ---------------------------------------------------------------------------
# Page setup
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title=f"{ASSISTANT_NAME} {VERSION} - War Room",
    page_icon="\u26a1",
    layout="wide",
    initial_sidebar_state="expanded",
)

WAR_ROOM_CSS = """
<style>
:root {
    --bg: #05070C;
    --bg-2: #0A0F1A;
    --neon: #00E5FF;
    --neon-dim: #007A8C;
    --accent: #1FFF8F;
    --warn: #FFB300;
    --err: #FF3366;
    --text: #D8F4FF;
}
html, body, [class^="css"], .stApp {
    background-color: var(--bg) !important;
    color: var(--text) !important;
    font-family: "JetBrains Mono", "Fira Code", Menlo, monospace;
}
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #050810 0%, #02040A 100%) !important;
    border-right: 1px solid rgba(0,229,255,0.25);
}
h1, h2, h3, h4 { color: var(--neon) !important; letter-spacing: 1px;
    text-shadow: 0 0 6px rgba(0,229,255,0.45); }
hr { border-top: 1px solid rgba(0,229,255,0.25); }
[data-testid="stMetricValue"] { color: var(--neon) !important;
    text-shadow: 0 0 8px rgba(0,229,255,0.5); }
[data-testid="stMetricDelta"] { color: var(--accent) !important; }
.stButton>button {
    background: transparent; color: var(--neon);
    border: 1px solid var(--neon); border-radius: 4px;
    box-shadow: 0 0 8px rgba(0,229,255,0.35);
}
.stButton>button:hover { background: rgba(0,229,255,0.1); }
.event-row { border-left: 3px solid var(--neon-dim); padding: 4px 10px; margin: 2px 0;
    background: rgba(0,229,255,0.04); border-radius: 2px; font-size: 12px; }
.event-row.INFO { border-color: var(--neon-dim); }
.event-row.WARN { border-color: var(--warn); color: var(--warn); }
.event-row.ERROR { border-color: var(--err); color: var(--err); }
.event-row.TRADE { border-color: var(--accent); color: var(--accent); }
.event-row.SIGNAL { border-color: var(--neon); }
.glow-panel { padding: 14px; border: 1px solid rgba(0,229,255,0.35);
    border-radius: 6px; background: rgba(0,229,255,0.03);
    box-shadow: 0 0 12px rgba(0,229,255,0.15) inset; }
.ticker { font-size: 12px; color: var(--neon); letter-spacing: 2px; }
</style>
"""
st.markdown(WAR_ROOM_CSS, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown(f"## {ASSISTANT_NAME}")
    st.markdown(f"<span class='ticker'>{VERSION} // OMNIPOTENCE</span>", unsafe_allow_html=True)
    st.markdown("---")
    st.markdown(f"**Sir-mode:** `{OWNER_TITLE}`")
    auto_refresh = st.toggle("Auto-Refresh (2s)", value=True)
    st.markdown("---")
    st.markdown("### Subsystems")
    st.markdown(
        "* Trader-Ultima\n"
        "* Vision / OS-Control\n"
        "* Ghost-Engine\n"
        "* Code-Forge\n"
        "* Voice-Bridge"
    )
    st.markdown("---")
    st.markdown("### Campaign")
    st.markdown(f"Start: **{TRADING.start_balance:.2f}**")
    st.markdown(f"Target: **{TRADING.target_balance:.2f}**")
    st.markdown(f"Risk/Trade: **{TRADING.risk_per_trade:.0%}**")
    st.markdown(f"Min Confluence: **{TRADING.min_confluence:.0%}**")

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
top_l, top_r = st.columns([3, 1])
with top_l:
    st.markdown(f"# {ASSISTANT_NAME} War Room")
    st.markdown(
        f"<span class='ticker'>"
        f"{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')} &nbsp; | &nbsp; "
        f"OPERATOR: {OWNER_TITLE.upper()}</span>",
        unsafe_allow_html=True,
    )
with top_r:
    st.markdown(
        "<div class='glow-panel'><b>SYSTEM</b><br/>"
        "<span style='color:#1FFF8F'>NOMINAL</span></div>",
        unsafe_allow_html=True,
    )

st.markdown("---")


# ---------------------------------------------------------------------------
# Data loaders
# ---------------------------------------------------------------------------
def _read_equity() -> pd.DataFrame:
    if not BRAIN.equity_log.exists():
        return pd.DataFrame(columns=["ts_iso", "balance", "equity"])
    try:
        df = pd.read_csv(BRAIN.equity_log)
        if "ts_iso" in df.columns:
            df["ts_iso"] = pd.to_datetime(df["ts_iso"], errors="coerce")
        return df.tail(800)
    except Exception:
        return pd.DataFrame(columns=["ts_iso", "balance", "equity"])


def _read_signals() -> pd.DataFrame:
    if not BRAIN.signals_log.exists():
        return pd.DataFrame()
    try:
        df = pd.read_csv(BRAIN.signals_log)
        if "ts_iso" in df.columns:
            df["ts_iso"] = pd.to_datetime(df["ts_iso"], errors="coerce")
        return df.tail(400)
    except Exception:
        return pd.DataFrame()


def _read_events(n: int = 200) -> List[dict]:
    return list(bus.tail_events(n))


def _read_news() -> List[dict]:
    p = RESEARCH_DIR / "news.json"
    if not p.exists():
        return []
    try:
        return json.loads(p.read_text(encoding="utf-8")).get("events", [])[:30]
    except Exception:
        return []


def _latest_screenshot() -> Path | None:
    candidates = sorted(SCREENSHOT_DIR.glob("*.png"), key=lambda x: x.stat().st_mtime, reverse=True)
    return candidates[0] if candidates else None


# ---------------------------------------------------------------------------
# KPI row
# ---------------------------------------------------------------------------
equity_df = _read_equity()
signals_df = _read_signals()
events = _read_events()

current_equity = float(equity_df["equity"].iloc[-1]) if not equity_df.empty else 0.0
current_balance = float(equity_df["balance"].iloc[-1]) if not equity_df.empty else 0.0
progress_pct = 0.0
if TRADING.target_balance > TRADING.start_balance:
    progress_pct = max(0.0, min(1.0, (current_balance - TRADING.start_balance) /
                                (TRADING.target_balance - TRADING.start_balance)))

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Balance", f"{current_balance:.2f}")
k2.metric("Equity", f"{current_equity:.2f}")
trade_events = [e for e in events if e.get("level") == "TRADE"]
k3.metric("Trades (session)", len(trade_events))
sig_count = 0 if signals_df.empty else int((signals_df["direction"] != "NONE").sum())
k4.metric("Live Signals", sig_count)
k5.metric("Campaign Progress", f"{progress_pct*100:.1f}%")

st.progress(progress_pct, text=f"{TRADING.start_balance:.0f} -> {TRADING.target_balance:.0f}")
st.markdown("---")

# ---------------------------------------------------------------------------
# Equity + Signals row
# ---------------------------------------------------------------------------
left, right = st.columns([2, 1])

with left:
    st.markdown("### Equity / Balance Curve")
    if equity_df.empty:
        st.info("Equity feed offline. Start the trader to populate logs/equity.csv.")
    else:
        chart_df = equity_df.set_index("ts_iso")[["balance", "equity"]]
        st.line_chart(chart_df, height=320, use_container_width=True)

with right:
    st.markdown("### Latest Confluence Signals")
    if signals_df.empty:
        st.info("No signals yet.")
    else:
        view = signals_df[["ts_iso", "symbol", "direction", "confluence"]].tail(12).iloc[::-1]
        view["confluence"] = view["confluence"].astype(float).map(lambda x: f"{x*100:.1f}%")
        st.dataframe(view, hide_index=True, use_container_width=True)

st.markdown("---")

# ---------------------------------------------------------------------------
# Vision + Ghost row
# ---------------------------------------------------------------------------
v_col, g_col = st.columns(2)
with v_col:
    st.markdown("### Vision Feed")
    shot = _latest_screenshot()
    if shot is None:
        st.info("No screenshots captured yet. Start controller.py to feed the vision panel.")
    else:
        st.image(str(shot), use_container_width=True, caption=shot.name)

with g_col:
    st.markdown("### Ghost / News Radar")
    news = _read_news()
    if not news:
        st.info("Ghost-engine has not delivered news yet.")
    else:
        for item in news[:8]:
            t = item.get("time", "")
            impact = (item.get("impact") or "").upper()
            color = {"HIGH": "var(--err)", "MEDIUM": "var(--warn)"}.get(impact, "var(--neon-dim)")
            st.markdown(
                f"<div class='event-row' style='border-color:{color}'>"
                f"<b>{t}</b> [{impact}] {item.get('currency','')} - {item.get('title','')}"
                "</div>",
                unsafe_allow_html=True,
            )

st.markdown("---")

# ---------------------------------------------------------------------------
# Live event log
# ---------------------------------------------------------------------------
st.markdown("### Live Event Stream")
if not events:
    st.info("No events yet. Bring agents online.")
else:
    for ev in events[-60:][::-1]:
        lvl = ev.get("level", "INFO")
        ts = ev.get("ts_iso", "")
        src = ev.get("source", "?")
        msg = ev.get("message", "")
        st.markdown(
            f"<div class='event-row {lvl}'>"
            f"<b>{ts}</b> · <span style='opacity:.7'>{src}</span> · {msg}"
            "</div>",
            unsafe_allow_html=True,
        )

# ---------------------------------------------------------------------------
# Auto-refresh
# ---------------------------------------------------------------------------
if auto_refresh:
    time.sleep(2)
    try:
        st.rerun()
    except AttributeError:  # Streamlit < 1.27
        st.experimental_rerun()
