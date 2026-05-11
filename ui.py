"""
J.A.R.V.I.S. V300 - WAR ROOM DASHBOARD
High-End Streamlit Interface | Deep-Black + Neon-Blue
"""

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from loguru import logger

from config.settings import DASHBOARD, TRADING, BASE_DIR, LOGS_DIR

# ── Page Config ──────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="J.A.R.V.I.S. V300 — WAR ROOM",
    page_icon="🔷",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── War Room CSS ─────────────────────────────────────────────────────────────

WAR_ROOM_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=JetBrains+Mono:wght@400;700&display=swap');

    :root {
        --neon-blue: #00d4ff;
        --neon-blue-dim: #0088aa;
        --neon-cyan: #00ffcc;
        --neon-red: #ff003c;
        --neon-green: #00ff88;
        --neon-orange: #ff8800;
        --bg-primary: #0a0a0f;
        --bg-secondary: #0d0d15;
        --bg-card: #111119;
        --border-glow: rgba(0, 212, 255, 0.3);
    }

    .stApp {
        background: var(--bg-primary);
        color: #c0c0c0;
        font-family: 'JetBrains Mono', monospace;
    }

    header[data-testid="stHeader"] {
        background: rgba(10, 10, 15, 0.95);
        backdrop-filter: blur(10px);
        border-bottom: 1px solid var(--border-glow);
    }

    .block-container {
        padding-top: 1rem;
        max-width: 100%;
    }

    h1, h2, h3 {
        font-family: 'Orbitron', sans-serif !important;
        color: var(--neon-blue) !important;
        text-shadow: 0 0 20px rgba(0, 212, 255, 0.5);
    }

    .war-room-title {
        font-family: 'Orbitron', sans-serif;
        font-size: 2.4rem;
        font-weight: 900;
        text-align: center;
        color: var(--neon-blue);
        text-shadow: 0 0 40px rgba(0, 212, 255, 0.6), 0 0 80px rgba(0, 212, 255, 0.3);
        letter-spacing: 6px;
        margin-bottom: 0.2rem;
        padding: 0.8rem 0;
        border-top: 1px solid var(--border-glow);
        border-bottom: 1px solid var(--border-glow);
    }

    .war-room-subtitle {
        text-align: center;
        color: var(--neon-blue-dim);
        font-size: 0.85rem;
        letter-spacing: 4px;
        margin-bottom: 1.5rem;
    }

    .metric-card {
        background: var(--bg-card);
        border: 1px solid var(--border-glow);
        border-radius: 8px;
        padding: 1rem 1.2rem;
        text-align: center;
        box-shadow: 0 0 15px rgba(0, 212, 255, 0.08);
        transition: box-shadow 0.3s;
    }

    .metric-card:hover {
        box-shadow: 0 0 25px rgba(0, 212, 255, 0.2);
    }

    .metric-label {
        font-family: 'Orbitron', sans-serif;
        font-size: 0.7rem;
        color: var(--neon-blue-dim);
        letter-spacing: 2px;
        text-transform: uppercase;
    }

    .metric-value {
        font-family: 'Orbitron', sans-serif;
        font-size: 1.8rem;
        font-weight: 700;
        color: var(--neon-blue);
        text-shadow: 0 0 15px rgba(0, 212, 255, 0.4);
    }

    .metric-value.positive { color: var(--neon-green); text-shadow: 0 0 15px rgba(0, 255, 136, 0.4); }
    .metric-value.negative { color: var(--neon-red); text-shadow: 0 0 15px rgba(255, 0, 60, 0.4); }

    .status-online {
        display: inline-block;
        width: 8px; height: 8px;
        background: var(--neon-green);
        border-radius: 50%;
        box-shadow: 0 0 8px var(--neon-green);
        animation: pulse-glow 2s infinite;
        margin-right: 6px;
    }

    .status-offline {
        display: inline-block;
        width: 8px; height: 8px;
        background: var(--neon-red);
        border-radius: 50%;
        box-shadow: 0 0 8px var(--neon-red);
        margin-right: 6px;
    }

    @keyframes pulse-glow {
        0%, 100% { opacity: 1; box-shadow: 0 0 8px var(--neon-green); }
        50% { opacity: 0.6; box-shadow: 0 0 16px var(--neon-green); }
    }

    .log-container {
        background: var(--bg-secondary);
        border: 1px solid var(--border-glow);
        border-radius: 6px;
        padding: 0.8rem;
        max-height: 350px;
        overflow-y: auto;
        font-size: 0.75rem;
        line-height: 1.6;
    }

    .log-entry { border-bottom: 1px solid rgba(0, 212, 255, 0.05); padding: 2px 0; }
    .log-time { color: var(--neon-blue-dim); }
    .log-info { color: var(--neon-blue); }
    .log-warn { color: var(--neon-orange); }
    .log-error { color: var(--neon-red); }
    .log-trade { color: var(--neon-green); }

    .agent-card {
        background: var(--bg-card);
        border: 1px solid var(--border-glow);
        border-radius: 8px;
        padding: 0.8rem;
        margin-bottom: 0.5rem;
    }

    .agent-name {
        font-family: 'Orbitron', sans-serif;
        font-size: 0.8rem;
        color: var(--neon-cyan);
        letter-spacing: 1px;
    }

    div[data-testid="stSidebar"] {
        background: var(--bg-secondary);
        border-right: 1px solid var(--border-glow);
    }

    .stButton>button {
        background: transparent;
        border: 1px solid var(--neon-blue);
        color: var(--neon-blue);
        font-family: 'Orbitron', sans-serif;
        letter-spacing: 2px;
        transition: all 0.3s;
    }

    .stButton>button:hover {
        background: rgba(0, 212, 255, 0.1);
        box-shadow: 0 0 20px rgba(0, 212, 255, 0.3);
    }
</style>
"""

st.markdown(WAR_ROOM_CSS, unsafe_allow_html=True)


# ── State Management ─────────────────────────────────────────────────────────

def init_state():
    defaults = {
        "equity_history": [],
        "trade_log": [],
        "system_log": [],
        "agent_status": {
            "TRADER": {"status": "STANDBY", "last_signal": "—", "win_rate": 0.0},
            "GHOST": {"status": "STANDBY", "last_scan": "—", "alerts": 0},
            "VISION": {"status": "STANDBY", "fps": 0, "detections": 0},
            "CODER": {"status": "STANDBY", "apps_built": 0, "errors": 0},
            "SECURITY": {"status": "STANDBY", "scans": 0, "issues": 0},
        },
        "total_pnl": 0.0,
        "total_trades": 0,
        "win_count": 0,
        "equity": 10.0,
        "running": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


init_state()


# ── Helper Functions ─────────────────────────────────────────────────────────

def add_system_log(message: str, level: str = "INFO"):
    ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    css_class = {
        "INFO": "log-info", "WARN": "log-warn",
        "ERROR": "log-error", "TRADE": "log-trade",
    }.get(level, "log-info")
    entry = f'<div class="log-entry"><span class="log-time">[{ts}]</span> <span class="{css_class}">[{level}]</span> {message}</div>'
    st.session_state.system_log.insert(0, entry)
    if len(st.session_state.system_log) > DASHBOARD["max_log_lines"]:
        st.session_state.system_log = st.session_state.system_log[:DASHBOARD["max_log_lines"]]


def metric_card(label: str, value: str, css_class: str = ""):
    val_class = f"metric-value {css_class}" if css_class else "metric-value"
    return f"""
    <div class="metric-card">
        <div class="metric-label">{label}</div>
        <div class="{val_class}">{value}</div>
    </div>
    """


def load_trade_history() -> pd.DataFrame:
    path = LOGS_DIR / "trade_history.csv"
    if path.exists():
        try:
            return pd.read_csv(path, parse_dates=["timestamp"])
        except Exception:
            pass
    return pd.DataFrame(columns=[
        "timestamp", "symbol", "direction", "lot", "entry", "exit",
        "sl", "tp", "pnl", "confluence", "strategy",
    ])


def load_equity_curve() -> list:
    path = LOGS_DIR / "equity_curve.json"
    if path.exists():
        try:
            with open(path) as f:
                return json.load(f)
        except Exception:
            pass
    return []


# ── Chart Builders ───────────────────────────────────────────────────────────

def build_equity_chart(equity_data: list) -> go.Figure:
    if not equity_data:
        now = datetime.now()
        equity_data = [
            {"time": (now - timedelta(minutes=i)).isoformat(), "equity": 10.0}
            for i in range(60, -1, -1)
        ]

    df = pd.DataFrame(equity_data)
    df["time"] = pd.to_datetime(df["time"])

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["time"], y=df["equity"],
        mode="lines",
        line=dict(color="#00d4ff", width=2),
        fill="tozeroy",
        fillcolor="rgba(0, 212, 255, 0.05)",
        name="Equity",
    ))

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#0a0a0f",
        plot_bgcolor="#0a0a0f",
        font=dict(family="JetBrains Mono", color="#808080"),
        title=dict(
            text="EQUITY CURVE",
            font=dict(family="Orbitron", size=14, color="#00d4ff"),
        ),
        xaxis=dict(
            gridcolor="rgba(0, 212, 255, 0.06)",
            showgrid=True, zeroline=False,
        ),
        yaxis=dict(
            gridcolor="rgba(0, 212, 255, 0.06)",
            showgrid=True, zeroline=False,
            title="EUR",
        ),
        height=320,
        margin=dict(l=40, r=20, t=40, b=30),
        showlegend=False,
    )
    return fig


def build_signals_chart() -> go.Figure:
    np.random.seed(int(time.time()) % 1000)
    n = DASHBOARD["chart_candles"]
    base = 1.0850
    close = base + np.cumsum(np.random.randn(n) * 0.0003)
    high = close + np.abs(np.random.randn(n) * 0.0002)
    low = close - np.abs(np.random.randn(n) * 0.0002)
    opn = close + np.random.randn(n) * 0.00015
    now = datetime.now()
    times = [now - timedelta(minutes=n - i) for i in range(n)]

    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True,
        row_heights=[0.75, 0.25],
        vertical_spacing=0.03,
    )

    fig.add_trace(go.Candlestick(
        x=times, open=opn, high=high, low=low, close=close,
        increasing_line_color="#00ff88",
        decreasing_line_color="#ff003c",
        name="Price",
    ), row=1, col=1)

    vol = np.abs(np.random.randn(n)) * 100
    colors = ["#00ff88" if close[i] >= opn[i] else "#ff003c" for i in range(n)]
    fig.add_trace(go.Bar(
        x=times, y=vol, marker_color=colors, opacity=0.4, name="Volume",
    ), row=2, col=1)

    fvg_zones = []
    for i in range(2, n - 1, 15):
        if high[i - 1] < low[i + 1]:
            fvg_zones.append((i, low[i + 1], high[i - 1], "bull"))
        elif low[i - 1] > high[i + 1]:
            fvg_zones.append((i, high[i + 1], low[i - 1], "bear"))

    for idx, y0, y1, ftype in fvg_zones:
        color = "rgba(0, 255, 136, 0.12)" if ftype == "bull" else "rgba(255, 0, 60, 0.12)"
        fig.add_shape(
            type="rect", x0=times[idx - 1], x1=times[min(idx + 5, n - 1)],
            y0=y0, y1=y1, fillcolor=color, line_width=0,
            row=1, col=1,
        )

    ob_indices = list(range(5, n, 20))
    for idx in ob_indices:
        if idx < n:
            is_bull = close[idx] > opn[idx]
            color = "rgba(0, 255, 204, 0.25)" if is_bull else "rgba(255, 136, 0, 0.25)"
            fig.add_shape(
                type="rect",
                x0=times[idx], x1=times[min(idx + 3, n - 1)],
                y0=low[idx], y1=high[idx],
                fillcolor=color, line_width=1,
                line_color="rgba(0, 255, 204, 0.5)" if is_bull else "rgba(255, 136, 0, 0.5)",
                row=1, col=1,
            )

    common = dict(
        template="plotly_dark",
        paper_bgcolor="#0a0a0f",
        plot_bgcolor="#0a0a0f",
        font=dict(family="JetBrains Mono", color="#808080"),
        title=dict(
            text=f"LIVE SIGNALS — {TRADING['symbol']} M1",
            font=dict(family="Orbitron", size=14, color="#00d4ff"),
        ),
        height=420,
        margin=dict(l=40, r=20, t=40, b=30),
        showlegend=False,
        xaxis_rangeslider_visible=False,
    )
    for axis in ["xaxis", "xaxis2", "yaxis", "yaxis2"]:
        common[axis] = dict(gridcolor="rgba(0, 212, 255, 0.06)", showgrid=True, zeroline=False)

    fig.update_layout(**common)
    return fig


def build_agent_panel() -> str:
    agents = st.session_state.agent_status
    html = ""
    for name, info in agents.items():
        is_online = info["status"] == "ACTIVE"
        dot = '<span class="status-online"></span>' if is_online else '<span class="status-offline"></span>'
        details = " | ".join(f"{k}: {v}" for k, v in info.items() if k != "status")
        html += f"""
        <div class="agent-card">
            <div class="agent-name">{dot}{name}</div>
            <div style="font-size:0.7rem; color:#808080; margin-top:4px;">{info['status']} — {details}</div>
        </div>
        """
    return html


# ── Main Dashboard Layout ────────────────────────────────────────────────────

def render():
    st.markdown('<div class="war-room-title">J.A.R.V.I.S. V300 — WAR ROOM</div>', unsafe_allow_html=True)
    st.markdown('<div class="war-room-subtitle">OMNIPOTENT AUTONOMOUS INTELLIGENCE SYSTEM</div>', unsafe_allow_html=True)

    trades_df = load_trade_history()
    equity_data = load_equity_curve()

    total_trades = len(trades_df) if not trades_df.empty else st.session_state.total_trades
    win_count = len(trades_df[trades_df["pnl"] > 0]) if not trades_df.empty else st.session_state.win_count
    win_rate = (win_count / total_trades * 100) if total_trades > 0 else 0.0
    total_pnl = trades_df["pnl"].sum() if not trades_df.empty else st.session_state.total_pnl
    equity = 10.0 + total_pnl

    pnl_class = "positive" if total_pnl >= 0 else "negative"
    pnl_sign = "+" if total_pnl >= 0 else ""

    m1, m2, m3, m4, m5 = st.columns(5)
    with m1:
        st.markdown(metric_card("EQUITY", f"€{equity:.2f}"), unsafe_allow_html=True)
    with m2:
        st.markdown(metric_card("P&L", f"{pnl_sign}€{total_pnl:.2f}", pnl_class), unsafe_allow_html=True)
    with m3:
        st.markdown(metric_card("TRADES", str(total_trades)), unsafe_allow_html=True)
    with m4:
        wr_class = "positive" if win_rate >= 60 else ("negative" if win_rate < 40 else "")
        st.markdown(metric_card("WIN RATE", f"{win_rate:.1f}%", wr_class), unsafe_allow_html=True)
    with m5:
        ts = datetime.now().strftime("%H:%M:%S")
        st.markdown(metric_card("SYSTEM TIME", ts), unsafe_allow_html=True)

    st.markdown("<div style='height: 1rem'></div>", unsafe_allow_html=True)

    col_chart, col_agents = st.columns([3, 1])

    with col_chart:
        st.plotly_chart(build_signals_chart(), use_container_width=True, key="signals")
        st.plotly_chart(build_equity_chart(equity_data), use_container_width=True, key="equity")

    with col_agents:
        st.markdown("### AGENT STATUS")
        st.markdown(build_agent_panel(), unsafe_allow_html=True)

        st.markdown("### RECENT TRADES")
        if not trades_df.empty:
            recent = trades_df.tail(10).iloc[::-1]
            for _, row in recent.iterrows():
                pnl_color = "#00ff88" if row["pnl"] >= 0 else "#ff003c"
                st.markdown(
                    f'<div class="agent-card">'
                    f'<span style="color:{pnl_color}">{"▲" if row["pnl"]>=0 else "▼"} '
                    f'{row["direction"]} {row["symbol"]}</span> '
                    f'<span style="color:#808080; font-size:0.7rem;">'
                    f'{row["lot"]}L @ {row["entry"]:.5f} → '
                    f'<span style="color:{pnl_color}">€{row["pnl"]:.2f}</span>'
                    f'</span></div>',
                    unsafe_allow_html=True,
                )
        else:
            st.markdown(
                '<div class="agent-card"><span style="color:#808080">No trades yet — system on standby</span></div>',
                unsafe_allow_html=True,
            )

    st.markdown("### SYSTEM LOG")
    if st.session_state.system_log:
        log_html = '<div class="log-container">' + "".join(st.session_state.system_log) + "</div>"
    else:
        now = datetime.now().strftime("%H:%M:%S")
        log_html = f"""
        <div class="log-container">
            <div class="log-entry"><span class="log-time">[{now}]</span> <span class="log-info">[INFO]</span> J.A.R.V.I.S. V300 War Room initialized</div>
            <div class="log-entry"><span class="log-time">[{now}]</span> <span class="log-info">[INFO]</span> All subsystems on standby — awaiting command, Sir</div>
        </div>
        """
    st.markdown(log_html, unsafe_allow_html=True)

    st.markdown("---")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        if st.button("▶ START TRADING", use_container_width=True):
            st.session_state.running = True
            add_system_log("Trading engine ACTIVATED — Sir, we are live.", "TRADE")
            st.rerun()
    with c2:
        if st.button("⏹ STOP ALL", use_container_width=True):
            st.session_state.running = False
            add_system_log("All systems HALTED by operator command.", "WARN")
            st.rerun()
    with c3:
        if st.button("🔄 REFRESH", use_container_width=True):
            st.rerun()
    with c4:
        if st.button("🧹 CLEAR LOG", use_container_width=True):
            st.session_state.system_log = []
            st.rerun()


if __name__ == "__main__":
    render()
