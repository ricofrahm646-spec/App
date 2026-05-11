"""JARVIS V300 War Room dashboard."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from controller import ScreenAnalyzer
from ghost_security import CodeAuditScanner
from trader_ultimate import Side, TraderUltimate, demo_rates


TRADER_LOG = Path("logs/trader_ultimate.jsonl")
CONTROLLER_LOG = Path("logs/controller.jsonl")


def page_config() -> None:
    st.set_page_config(
        page_title="JARVIS V300 War Room",
        page_icon="J",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(
        """
        <style>
        :root {
            --jarvis-bg: #02040a;
            --jarvis-panel: rgba(7, 18, 34, 0.84);
            --jarvis-blue: #00d5ff;
            --jarvis-blue-soft: rgba(0, 213, 255, 0.18);
            --jarvis-text: #e9fbff;
            --jarvis-muted: #7a94a7;
        }
        .stApp {
            background:
              radial-gradient(circle at top left, rgba(0, 213, 255, 0.17), transparent 28rem),
              radial-gradient(circle at bottom right, rgba(16, 80, 255, 0.13), transparent 34rem),
              var(--jarvis-bg);
            color: var(--jarvis-text);
        }
        [data-testid="stMetric"] {
            background: linear-gradient(145deg, rgba(0, 213, 255, 0.14), rgba(3, 8, 18, 0.92));
            border: 1px solid rgba(0, 213, 255, 0.42);
            box-shadow: 0 0 22px rgba(0, 213, 255, 0.15);
            border-radius: 18px;
            padding: 16px;
        }
        .jarvis-panel {
            background: var(--jarvis-panel);
            border: 1px solid rgba(0, 213, 255, 0.35);
            border-radius: 20px;
            padding: 18px 20px;
            box-shadow: inset 0 0 28px rgba(0, 213, 255, 0.08), 0 0 32px rgba(0, 0, 0, 0.42);
            margin-bottom: 16px;
        }
        .jarvis-title {
            font-size: 3rem;
            letter-spacing: .18rem;
            font-weight: 800;
            text-shadow: 0 0 18px rgba(0, 213, 255, 0.65);
            margin-bottom: 0;
        }
        .jarvis-subtitle {
            color: var(--jarvis-muted);
            letter-spacing: .08rem;
            margin-top: -8px;
        }
        .status-ok { color: #2fffc5; font-weight: 700; }
        .status-warn { color: #ffd166; font-weight: 700; }
        .status-block { color: #ff5c8a; font-weight: 700; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def neon_template(fig: go.Figure) -> go.Figure:
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0.18)",
        font={"color": "#dff9ff"},
        margin={"l": 24, "r": 24, "t": 42, "b": 24},
        xaxis={"gridcolor": "rgba(0, 213, 255, 0.10)"},
        yaxis={"gridcolor": "rgba(0, 213, 255, 0.10)"},
        legend={"orientation": "h"},
    )
    return fig


def read_jsonl(path: Path, limit: int = 200) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()[-limit:]
    rows: list[dict[str, Any]] = []
    for line in lines:
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            rows.append({"raw": line})
    return rows


def equity_curve() -> pd.DataFrame:
    rows = read_jsonl(TRADER_LOG, 400)
    if not rows:
        rng = np.random.default_rng(300)
        timestamps = pd.date_range(end=pd.Timestamp.utcnow(), periods=160, freq="min")
        equity = 10 + np.cumsum(rng.normal(0.012, 0.07, len(timestamps)))
        equity = np.maximum(0, equity)
        return pd.DataFrame({"time": timestamps, "equity": equity, "mode": "simulated"})
    values: list[dict[str, Any]] = []
    equity = 10.0
    for idx, row in enumerate(rows):
        confidence = float(row.get("confidence", 0.0) or 0.0)
        side = row.get("side", "HOLD")
        if side in {"BUY", "SELL"}:
            equity += (confidence - 0.5) * 0.12
        values.append(
            {
                "time": pd.to_datetime(row.get("timestamp", datetime.now(timezone.utc).isoformat())),
                "equity": equity,
                "mode": "log-derived",
                "confidence": confidence,
            }
        )
    return pd.DataFrame(values)


def equity_panel() -> None:
    data = equity_curve()
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=data["time"],
            y=data["equity"],
            mode="lines",
            name="Equity",
            line={"color": "#00d5ff", "width": 3},
            fill="tozeroy",
            fillcolor="rgba(0, 213, 255, 0.14)",
        )
    )
    fig.add_hline(y=10, line_dash="dot", line_color="rgba(255,255,255,0.28)")
    fig.update_layout(title="Equity Telemetry")
    st.plotly_chart(neon_template(fig), use_container_width=True)


def signal_panel() -> None:
    engine = TraderUltimate()
    signal = engine.generate_signal(demo_rates())
    color = "#2fffc5" if signal.side is not Side.HOLD else "#ffd166"
    st.markdown('<div class="jarvis-panel">', unsafe_allow_html=True)
    st.subheader("Trading-Ultima Agent Signal")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Side", signal.side.value)
    c2.metric("Confluence", f"{signal.confidence:.0%}")
    c3.metric("Entry", f"{signal.entry:.5f}" if signal.entry else "WAIT")
    c4.metric("Risk Mode", "PAPER")
    st.markdown(f"<span style='color:{color};font-weight:700'>Reason Matrix</span>", unsafe_allow_html=True)
    for reason in signal.reasons:
        st.write(f"- {reason}")
    st.caption("Live execution requires MT5 plus explicit risk acknowledgement environment variables.")
    st.markdown("</div>", unsafe_allow_html=True)


def candles_panel() -> None:
    data = demo_rates(120)
    fig = go.Figure(
        data=[
            go.Candlestick(
                x=data["time"],
                open=data["open"],
                high=data["high"],
                low=data["low"],
                close=data["close"],
                increasing_line_color="#2fffc5",
                decreasing_line_color="#ff5c8a",
                name="M1",
            )
        ]
    )
    fig.update_layout(title="M1 Tactical Chart", xaxis_rangeslider_visible=False)
    st.plotly_chart(neon_template(fig), use_container_width=True)


def status_panel() -> None:
    st.markdown('<div class="jarvis-panel">', unsafe_allow_html=True)
    st.subheader("System Status Logs")
    trader_rows = read_jsonl(TRADER_LOG, 12)
    controller_rows = read_jsonl(CONTROLLER_LOG, 12)
    if not trader_rows and not controller_rows:
        st.info("No live logs yet. Start engines from the sidebar or SYSTEM_IGNITION.bat.")
    if trader_rows:
        st.write("Trading Log")
        st.dataframe(pd.DataFrame(trader_rows), use_container_width=True, hide_index=True)
    if controller_rows:
        st.write("Controller Log")
        st.dataframe(pd.DataFrame(controller_rows), use_container_width=True, hide_index=True)
    st.markdown("</div>", unsafe_allow_html=True)


def security_panel() -> None:
    st.markdown('<div class="jarvis-panel">', unsafe_allow_html=True)
    st.subheader("Ghost-Security Audit")
    if st.button("Run code audit", type="primary"):
        findings = CodeAuditScanner(Path(".")).scan()
        if findings:
            st.warning(f"{len(findings)} findings detected")
            st.dataframe(pd.DataFrame([item.__dict__ for item in findings]), use_container_width=True, hide_index=True)
        else:
            st.success("No findings detected by local scanner.")
    else:
        st.caption("Scanner checks hard-coded secrets, dangerous dynamic execution, and risky shell usage.")
    st.markdown("</div>", unsafe_allow_html=True)


def vision_panel() -> None:
    st.markdown('<div class="jarvis-panel">', unsafe_allow_html=True)
    st.subheader("Vision Matrix")
    st.caption("Screen analysis is for charts and accessibility workflows. Game automation is blocked.")
    if st.button("Analyze current screen"):
        analyzer = ScreenAnalyzer()
        try:
            result = analyzer.analyze_screen()
            st.json(result)
        except Exception as exc:
            st.error(f"Screen capture unavailable: {exc}")
    st.markdown("</div>", unsafe_allow_html=True)


def sidebar() -> None:
    st.sidebar.title("JARVIS Controls")
    st.sidebar.markdown("**Mode:** <span class='status-warn'>Safe Autonomous</span>", unsafe_allow_html=True)
    st.sidebar.caption("Sir, the system is online with risk gates enabled.")
    st.sidebar.divider()
    st.sidebar.write("Subsystems")
    st.sidebar.checkbox("Trading-Ultima", value=True)
    st.sidebar.checkbox("Vision Matrix", value=True)
    st.sidebar.checkbox("Ghost-Security", value=True)
    st.sidebar.checkbox("Coder Core", value=True)
    st.sidebar.divider()
    st.sidebar.warning("Live trading and OS control are disabled unless explicitly enabled outside the UI.")


def main() -> None:
    page_config()
    sidebar()
    st.markdown("<h1 class='jarvis-title'>JARVIS V300 WAR ROOM</h1>", unsafe_allow_html=True)
    st.markdown("<p class='jarvis-subtitle'>Omni-system telemetry for trading, coding, vision, and security. Welcome, Sir.</p>", unsafe_allow_html=True)

    top = st.columns(4)
    top[0].metric("Core", "ONLINE", "Safe gates active")
    top[1].metric("Trading", "PAPER", "MT5-ready")
    top[2].metric("Vision", "READY", "No game automation")
    top[3].metric("Security", "ARMED", "Local audit")

    left, right = st.columns([1.35, 1])
    with left:
        equity_panel()
        candles_panel()
    with right:
        signal_panel()
        vision_panel()
        security_panel()
    status_panel()


if __name__ == "__main__":
    main()
