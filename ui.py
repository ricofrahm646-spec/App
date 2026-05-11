from __future__ import annotations

import time
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from ghost_security import GhostSecurity
from jarvis import JarvisCore
from trader_ultimate import TraderUltimate


st.set_page_config(page_title="JARVIS War Room", page_icon="J", layout="wide")


WAR_ROOM_CSS = """
<style>
    .stApp {
        background: radial-gradient(circle at top, #0a1b2f 0%, #03060b 38%, #010203 100%);
        color: #dff8ff;
    }
    .block-container {
        padding-top: 1.2rem;
    }
    .jarvis-panel {
        border: 1px solid rgba(0, 225, 255, 0.35);
        background: rgba(3, 12, 20, 0.88);
        box-shadow: 0 0 22px rgba(0, 170, 255, 0.18);
        border-radius: 18px;
        padding: 1rem 1.1rem;
    }
    .jarvis-title {
        font-size: 1.1rem;
        font-weight: 700;
        color: #7be7ff;
        letter-spacing: 0.08rem;
    }
    .jarvis-kpi {
        font-size: 1.8rem;
        font-weight: 700;
        color: #00d9ff;
    }
    div[data-testid="stMetric"] {
        background: rgba(2, 15, 24, 0.8);
        border: 1px solid rgba(0, 225, 255, 0.18);
        padding: 0.8rem;
        border-radius: 14px;
    }
</style>
"""


def ensure_state() -> None:
    if "trader" not in st.session_state:
        st.session_state.trader = TraderUltimate(symbol="EURUSD", mode="paper")
    if "security" not in st.session_state:
        st.session_state.security = GhostSecurity(Path.cwd())
    if "jarvis" not in st.session_state:
        st.session_state.jarvis = JarvisCore(workspace_root=Path.cwd(), symbol="EURUSD", mode="paper")
    if "audit_report" not in st.session_state:
        st.session_state.audit_report = {"finding_count": 0, "findings": []}
    if "research_digest" not in st.session_state:
        st.session_state.research_digest = {"headline_count": 0, "headlines": []}


def build_equity_figure(equity_curve: list[dict]) -> go.Figure:
    df = pd.DataFrame(equity_curve)
    figure = go.Figure()
    if not df.empty:
        figure.add_trace(
            go.Scatter(
                x=df["time"],
                y=df["equity"],
                mode="lines+markers",
                line={"color": "#00d9ff", "width": 3},
                marker={"size": 6, "color": "#7be7ff"},
                name="Equity",
            )
        )
        figure.add_trace(
            go.Scatter(
                x=df["time"],
                y=df["balance"],
                mode="lines",
                line={"color": "#0055ff", "width": 2, "dash": "dot"},
                name="Balance",
            )
        )
    figure.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin={"l": 10, "r": 10, "t": 30, "b": 10},
        title="Equity Command Curve",
    )
    return figure


def build_price_figure(candles: list[dict], signals: list[dict]) -> go.Figure:
    df = pd.DataFrame(candles)
    figure = go.Figure()
    if not df.empty:
        figure.add_trace(
            go.Candlestick(
                x=df["time"],
                open=df["open"],
                high=df["high"],
                low=df["low"],
                close=df["close"],
                increasing_line_color="#00d9ff",
                decreasing_line_color="#ff4d7d",
                name="M1",
            )
        )

        if signals:
            signal_df = pd.DataFrame(signals)
            figure.add_trace(
                go.Scatter(
                    x=signal_df["detected_at"],
                    y=signal_df["entry"],
                    mode="markers",
                    marker={
                        "size": 12,
                        "color": signal_df["direction"].map({"buy": "#00ffb3", "sell": "#ff4d7d"}),
                        "symbol": signal_df["direction"].map({"buy": "triangle-up", "sell": "triangle-down"}),
                    },
                    name="Agent Signals",
                )
            )

    figure.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin={"l": 10, "r": 10, "t": 30, "b": 10},
        title="M1 Battlefield",
        xaxis_rangeslider_visible=False,
    )
    return figure


ensure_state()
st.markdown(WAR_ROOM_CSS, unsafe_allow_html=True)

sidebar = st.sidebar
sidebar.header("Mission Control")
symbol = sidebar.selectbox("Symbol", ["EURUSD", "GBPUSD", "USDJPY", "XAUUSD"], index=0)
mode = sidebar.selectbox("Mode", ["paper", "live"], index=0)
auto_refresh = sidebar.checkbox("Auto refresh", value=False)

if symbol != st.session_state.trader.symbol or mode != st.session_state.trader.mode:
    st.session_state.trader = TraderUltimate(symbol=symbol, mode=mode)
    st.session_state.jarvis = JarvisCore(workspace_root=Path.cwd(), symbol=symbol, mode=mode)

control_col_1, control_col_2, control_col_3 = sidebar.columns(3)
if control_col_1.button("Scan"):
    st.session_state.trader.run_cycle()
if control_col_2.button("Audit"):
    st.session_state.audit_report = st.session_state.security.run_audit()
if control_col_3.button("News"):
    st.session_state.research_digest = st.session_state.security.market_research_digest()

snapshot = st.session_state.trader.run_cycle()
signals = snapshot.recent_signals
latest_signal = snapshot.latest_signal or {}
diagnostics = snapshot.diagnostics or {}

st.title("JARVIS V300 OMNIPOTENCE // WAR ROOM")
st.caption("Unified command console for trading intelligence, code generation, research and operator-controlled automation.")

kpi_1, kpi_2, kpi_3, kpi_4 = st.columns(4)
kpi_1.metric("Balance", f"{snapshot.balance:,.2f}")
kpi_2.metric("Equity", f"{snapshot.equity:,.2f}")
kpi_3.metric("Open Positions", str(snapshot.open_positions))
kpi_4.metric("Confluence", f"{latest_signal.get('confluence', 0):.2f}")

top_left, top_right = st.columns([1.4, 1.0], gap="large")
with top_left:
    st.markdown('<div class="jarvis-panel"><div class="jarvis-title">EQUITY / SIGNAL GRID</div></div>', unsafe_allow_html=True)
    st.plotly_chart(build_equity_figure(st.session_state.trader.equity_curve()), use_container_width=True)
    st.plotly_chart(build_price_figure(snapshot.recent_candles, signals), use_container_width=True)

with top_right:
    st.markdown('<div class="jarvis-panel"><div class="jarvis-title">AGENT STATUS</div></div>', unsafe_allow_html=True)
    status_rows = [
        {"Agent": "TRADING-ULTIMA", "Status": "ONLINE", "Detail": f"{snapshot.symbol} / {snapshot.mode.upper()}"},
        {"Agent": "GHOST-SECURITY", "Status": "ONLINE", "Detail": f"{st.session_state.audit_report['finding_count']} findings"},
        {"Agent": "RESEARCH", "Status": "ONLINE", "Detail": f"{st.session_state.research_digest['headline_count']} headlines"},
        {"Agent": "CODER", "Status": "ONLINE", "Detail": f"{len(st.session_state.jarvis.coder.list_apps())} apps"},
    ]
    st.dataframe(pd.DataFrame(status_rows), use_container_width=True, hide_index=True)
    st.json(
        {
            "latest_signal": latest_signal,
            "diagnostics": diagnostics,
            "recent_headlines": st.session_state.research_digest["headlines"][:5],
        },
        expanded=False,
    )

bottom_left, bottom_right = st.columns([1.0, 1.0], gap="large")
with bottom_left:
    st.markdown('<div class="jarvis-panel"><div class="jarvis-title">SYSTEM LOGS</div></div>', unsafe_allow_html=True)
    log_df = pd.DataFrame({"log": snapshot.logs[:20]})
    st.dataframe(log_df, use_container_width=True, hide_index=True)

with bottom_right:
    st.markdown('<div class="jarvis-panel"><div class="jarvis-title">SECURITY & APP FACTORY</div></div>', unsafe_allow_html=True)
    app_name = st.text_input("App name", value="ops_console")
    app_spec = st.text_area(
        "Specification",
        value="A visual dashboard for operators with health metrics, charts and a compact control panel.",
        height=120,
    )
    if st.button("Generate app in /apps"):
        generated = st.session_state.jarvis.coder.generate_app(app_name, app_spec)
        st.success(f"Generated {generated.name} via template {generated.template}")
        st.json(generated.to_dict(), expanded=False)

    st.dataframe(
        pd.DataFrame(st.session_state.audit_report.get("findings", [])),
        use_container_width=True,
        hide_index=True,
    )

if auto_refresh:
    time.sleep(2)
    st.rerun()
