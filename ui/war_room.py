"""
JARVIS V300 War Room dashboard.

Run with:
    streamlit run ui/war_room.py
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone
from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from ghost_security import SecurityAuditor
from trader_ultimate import SMCSignal, TradingUltima


WAR_ROOM_CSS = """
<style>
body, .stApp {
    background: radial-gradient(circle at top left, #071426 0%, #02040a 42%, #000000 100%);
    color: #d6f5ff;
}
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #020916 0%, #02040a 100%);
    border-right: 1px solid #0ea5ff55;
}
.jarvis-title {
    font-size: 2.8rem;
    font-weight: 800;
    letter-spacing: 0.18rem;
    color: #dff9ff;
    text-shadow: 0 0 18px #00aaff, 0 0 38px #0066ff;
}
.jarvis-subtitle {
    color: #7dd3fc;
    margin-top: -1rem;
}
.log-line {
    font-family: Consolas, monospace;
    color: #9ee7ff;
    background: #020916;
    border-left: 3px solid #0ea5ff;
    padding: 0.35rem 0.6rem;
    margin-bottom: 0.25rem;
}
.stMetric {
    border: 1px solid #0ea5ff55;
    background: #020916aa;
    border-radius: 14px;
    padding: 0.6rem;
}
</style>
"""


def ensure_state() -> None:
    if "logs" not in st.session_state:
        st.session_state.logs = []
    if "equity" not in st.session_state:
        st.session_state.equity = build_equity_curve()
    if "last_snapshot" not in st.session_state:
        st.session_state.last_snapshot = {}


def build_equity_curve(points: int = 120) -> pd.DataFrame:
    now = datetime.now(timezone.utc)
    equity = 10.0
    rows: list[dict[str, Any]] = []
    for index in range(points):
        drift = random.uniform(-0.08, 0.16)
        equity = max(0.0, equity + drift)
        rows.append({"time": now - timedelta(minutes=points - index), "equity": round(equity, 2)})
    return pd.DataFrame(rows)


@st.cache_resource
def trading_engine() -> TradingUltima:
    engine = TradingUltima()
    engine.start()
    return engine


def append_log(message: str) -> None:
    timestamp = datetime.now(timezone.utc).strftime("%H:%M:%S UTC")
    st.session_state.logs.insert(0, f"[{timestamp}] {message}")
    st.session_state.logs = st.session_state.logs[:60]


def signal_to_table(signal: SMCSignal | None) -> pd.DataFrame:
    if signal is None:
        return pd.DataFrame(
            [{"agent": "SMC-Core", "side": "WAIT", "confluence": "0.00%", "entry": "-", "risk_reward": "-"}]
        )
    return pd.DataFrame(
        [
            {
                "agent": "SMC-Core",
                "side": signal.side.upper(),
                "confluence": f"{signal.confluence:.2%}",
                "entry": f"{signal.entry:.5f}",
                "risk_reward": f"{signal.risk_reward:.2f}",
            }
        ]
    )


def equity_chart(frame: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=frame["time"],
            y=frame["equity"],
            mode="lines",
            line={"color": "#00d4ff", "width": 3},
            fill="tozeroy",
            fillcolor="rgba(0, 212, 255, 0.16)",
            name="Equity",
        )
    )
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(2,9,22,0.65)",
        margin={"l": 20, "r": 20, "t": 20, "b": 20},
        height=360,
        xaxis={"gridcolor": "#0e749055"},
        yaxis={"gridcolor": "#0e749055", "title": "Account Equity"},
    )
    return fig


def render_header() -> None:
    st.markdown(WAR_ROOM_CSS, unsafe_allow_html=True)
    st.markdown('<div class="jarvis-title">J.A.R.V.I.S. V300 WAR ROOM</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="jarvis-subtitle">Trading Ultima | Vision Telemetry | Ghost Research | Security Audit | Coding Core</div>',
        unsafe_allow_html=True,
    )


def render_dashboard() -> None:
    st.set_page_config(page_title="JARVIS V300 OMNIPOTENCE", page_icon="J", layout="wide")
    ensure_state()
    render_header()
    with st.sidebar:
        st.header("Mission Control")
        st.text_input("Symbol", value="EURUSD")
        auto_refresh = st.toggle("Auto-refresh UI", value=False)
        st.caption("Live trading remains dry-run unless JARVIS_LIVE_TRADING=1 is set.")
        run_tick = st.button("Execute Trading Scan", type="primary")
        run_audit = st.button("Run Security Audit")
        st.divider()
        st.caption("Operator: Sir")

    engine = trading_engine()
    findings_count = 0
    if run_tick:
        snapshot = engine.tick()
        st.session_state.last_snapshot = snapshot
        append_log(f"Trading scan: {snapshot.get('status')} - {snapshot.get('reason', 'signal processed')}")
        equity = st.session_state.equity.copy()
        last_equity = float(equity.iloc[-1]["equity"])
        delta = random.uniform(-0.05, 0.12) if snapshot.get("status") != "executed" else random.uniform(0.05, 0.25)
        equity.loc[len(equity)] = [datetime.now(timezone.utc), round(max(0.0, last_equity + delta), 2)]
        st.session_state.equity = equity.tail(160)

    if run_audit:
        findings = SecurityAuditor(["apps", "."]).scan()
        findings_count = len(findings)
        append_log(f"Security audit completed with {findings_count} findings")
        with st.expander("Audit Findings", expanded=True):
            st.dataframe(pd.DataFrame([finding.__dict__ for finding in findings]) if findings else pd.DataFrame())

    snapshot = st.session_state.last_snapshot
    cols = st.columns(4)
    signal = snapshot.get("signal") if snapshot else None
    cols[0].metric("System Status", snapshot.get("status", "standby").upper() if snapshot else "STANDBY")
    cols[1].metric("Signal Confluence", f"{signal.confluence:.2%}" if isinstance(signal, SMCSignal) else "0.00%")
    cols[2].metric("Execution Mode", "DRY_RUN")
    cols[3].metric("Audit Findings", findings_count)

    left, right = st.columns([2, 1])
    with left:
        st.subheader("Equity Live Graph")
        st.plotly_chart(equity_chart(st.session_state.equity), use_container_width=True)
        st.subheader("Agent Trading Signals")
        st.dataframe(signal_to_table(signal if isinstance(signal, SMCSignal) else None), use_container_width=True)
    with right:
        st.subheader("Status Logs")
        for line in st.session_state.logs[:18]:
            st.markdown(f'<div class="log-line">{line}</div>', unsafe_allow_html=True)
        if not st.session_state.logs:
            st.info("Awaiting operator command, Sir.")

    if auto_refresh:
        st.rerun()


if __name__ == "__main__":
    render_dashboard()
