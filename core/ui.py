"""
J.A.R.V.I.S. V300 - WAR ROOM DASHBOARD
High-end Streamlit interface with deep-black & neon-blue aesthetic.
Live equity curves, trading signals, agent status, and system logs.
"""
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

sys.path.insert(0, str(Path(__file__).parent.parent))
from config.settings import JarvisConfig


# ── Theme Constants ──────────────────────────────────────────────────────────

BG_PRIMARY = "#0a0a0f"
BG_SECONDARY = "#111118"
BG_CARD = "#16161f"
ACCENT = "#00d4ff"
ACCENT_DIM = "#005f73"
SUCCESS = "#00ff88"
DANGER = "#ff3366"
WARNING = "#ffaa00"
TEXT_PRIMARY = "#e0e0e8"
TEXT_DIM = "#6b6b80"
GRID_COLOR = "#1a1a2e"


def inject_css():
    st.markdown(f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;500;700&family=Inter:wght@300;400;600;700&display=swap');

        .stApp {{
            background-color: {BG_PRIMARY};
            color: {TEXT_PRIMARY};
            font-family: 'Inter', sans-serif;
        }}

        header[data-testid="stHeader"] {{
            background-color: {BG_PRIMARY} !important;
            border-bottom: 1px solid {ACCENT_DIM};
        }}

        .stSidebar > div {{
            background-color: {BG_SECONDARY} !important;
            border-right: 1px solid {ACCENT_DIM};
        }}

        .metric-card {{
            background: linear-gradient(135deg, {BG_CARD}, {BG_SECONDARY});
            border: 1px solid {ACCENT_DIM};
            border-radius: 12px;
            padding: 20px;
            text-align: center;
            box-shadow: 0 0 20px rgba(0, 212, 255, 0.05);
            transition: box-shadow 0.3s;
        }}
        .metric-card:hover {{
            box-shadow: 0 0 30px rgba(0, 212, 255, 0.15);
        }}

        .metric-value {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 2rem;
            font-weight: 700;
            margin: 8px 0 4px;
        }}
        .metric-label {{
            font-size: 0.75rem;
            color: {TEXT_DIM};
            text-transform: uppercase;
            letter-spacing: 2px;
        }}

        .signal-badge {{
            display: inline-block;
            padding: 4px 16px;
            border-radius: 20px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.85rem;
            font-weight: 600;
        }}
        .signal-buy {{ background: rgba(0,255,136,0.15); color: {SUCCESS}; border: 1px solid {SUCCESS}; }}
        .signal-sell {{ background: rgba(255,51,102,0.15); color: {DANGER}; border: 1px solid {DANGER}; }}
        .signal-neutral {{ background: rgba(107,107,128,0.15); color: {TEXT_DIM}; border: 1px solid {TEXT_DIM}; }}

        .war-room-title {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 1.5rem;
            color: {ACCENT};
            text-shadow: 0 0 20px rgba(0,212,255,0.4);
            letter-spacing: 4px;
            text-transform: uppercase;
            border-bottom: 1px solid {ACCENT_DIM};
            padding-bottom: 10px;
            margin-bottom: 20px;
        }}

        .log-entry {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.78rem;
            padding: 4px 8px;
            border-left: 3px solid {ACCENT_DIM};
            margin: 2px 0;
            background: rgba(10,10,15,0.6);
        }}
        .log-info {{ border-left-color: {ACCENT}; }}
        .log-success {{ border-left-color: {SUCCESS}; }}
        .log-warning {{ border-left-color: {WARNING}; }}
        .log-danger {{ border-left-color: {DANGER}; }}

        .agent-status {{
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 8px 14px;
            margin: 4px 0;
            background: {BG_CARD};
            border-radius: 8px;
            border: 1px solid {ACCENT_DIM};
        }}
        .status-dot {{
            width: 10px;
            height: 10px;
            border-radius: 50%;
            display: inline-block;
        }}
        .status-active {{ background: {SUCCESS}; box-shadow: 0 0 8px {SUCCESS}; }}
        .status-idle {{ background: {WARNING}; }}
        .status-error {{ background: {DANGER}; box-shadow: 0 0 8px {DANGER}; }}

        div[data-testid="stMetric"] {{
            background: {BG_CARD};
            border: 1px solid {ACCENT_DIM};
            border-radius: 10px;
            padding: 12px;
        }}
        div[data-testid="stMetric"] label {{
            color: {TEXT_DIM} !important;
        }}
        div[data-testid="stMetric"] div[data-testid="stMetricValue"] {{
            color: {ACCENT} !important;
            font-family: 'JetBrains Mono', monospace !important;
        }}

        .stTabs [data-baseweb="tab-list"] {{
            gap: 4px;
            background-color: {BG_SECONDARY};
            border-radius: 8px;
            padding: 4px;
        }}
        .stTabs [data-baseweb="tab"] {{
            color: {TEXT_DIM};
            border-radius: 6px;
        }}
        .stTabs [aria-selected="true"] {{
            color: {ACCENT} !important;
            background-color: {BG_CARD} !important;
        }}
    </style>
    """, unsafe_allow_html=True)


def metric_card(label: str, value: str, color: str = ACCENT) -> str:
    return f"""
    <div class="metric-card">
        <div class="metric-label">{label}</div>
        <div class="metric-value" style="color: {color};">{value}</div>
    </div>
    """


def signal_badge(direction: str) -> str:
    cls = "signal-buy" if direction == "BUY" else "signal-sell" if direction == "SELL" else "signal-neutral"
    return f'<span class="signal-badge {cls}">{direction}</span>'


def agent_status_row(name: str, status: str) -> str:
    dot_cls = "status-active" if status == "ACTIVE" else "status-idle" if status == "IDLE" else "status-error"
    return f"""
    <div class="agent-status">
        <span class="status-dot {dot_cls}"></span>
        <span style="color: {TEXT_PRIMARY}; font-family: 'JetBrains Mono', monospace; font-size: 0.85rem;">{name}</span>
        <span style="color: {TEXT_DIM}; margin-left: auto; font-size: 0.75rem;">{status}</span>
    </div>
    """


def create_equity_chart(equity_data: list[float]) -> go.Figure:
    if not equity_data:
        equity_data = [10.0]

    fig = go.Figure()
    x = list(range(len(equity_data)))

    color_line = SUCCESS if equity_data[-1] >= equity_data[0] else DANGER

    fig.add_trace(go.Scatter(
        x=x, y=equity_data,
        mode="lines",
        line=dict(color=color_line, width=2),
        fill="tozeroy",
        fillcolor=f"rgba({','.join(str(int(color_line[i:i+2], 16)) for i in (1, 3, 5))}, 0.08)",
        name="Equity",
    ))

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor=BG_CARD,
        plot_bgcolor=BG_PRIMARY,
        margin=dict(l=40, r=20, t=30, b=30),
        height=300,
        xaxis=dict(showgrid=True, gridcolor=GRID_COLOR, zeroline=False),
        yaxis=dict(showgrid=True, gridcolor=GRID_COLOR, zeroline=False, title="Equity (€)"),
        font=dict(family="JetBrains Mono", color=TEXT_DIM),
        showlegend=False,
    )
    return fig


def create_candlestick_chart(df: pd.DataFrame, signals: list = None) -> go.Figure:
    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True,
        vertical_spacing=0.03, row_heights=[0.75, 0.25],
    )

    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df["open"], high=df["high"], low=df["low"], close=df["close"],
        increasing_line_color=SUCCESS, decreasing_line_color=DANGER,
        increasing_fillcolor=SUCCESS, decreasing_fillcolor=DANGER,
        name="Price",
    ), row=1, col=1)

    if signals:
        buy_signals = [s for s in signals if s.get("direction") == "BUY"]
        sell_signals = [s for s in signals if s.get("direction") == "SELL"]

        if buy_signals:
            fig.add_trace(go.Scatter(
                x=[s["time"] for s in buy_signals],
                y=[s["price"] for s in buy_signals],
                mode="markers",
                marker=dict(symbol="triangle-up", size=14, color=SUCCESS, line=dict(width=1, color="white")),
                name="BUY",
            ), row=1, col=1)

        if sell_signals:
            fig.add_trace(go.Scatter(
                x=[s["time"] for s in sell_signals],
                y=[s["price"] for s in sell_signals],
                mode="markers",
                marker=dict(symbol="triangle-down", size=14, color=DANGER, line=dict(width=1, color="white")),
                name="SELL",
            ), row=1, col=1)

    if "tick_volume" in df.columns:
        colors = [SUCCESS if df["close"].iloc[i] >= df["open"].iloc[i] else DANGER for i in range(len(df))]
        fig.add_trace(go.Bar(
            x=df.index, y=df["tick_volume"],
            marker_color=colors, opacity=0.4, name="Volume",
        ), row=2, col=1)

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor=BG_CARD,
        plot_bgcolor=BG_PRIMARY,
        margin=dict(l=50, r=20, t=30, b=30),
        height=450,
        xaxis_rangeslider_visible=False,
        font=dict(family="JetBrains Mono", color=TEXT_DIM),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )

    for i in range(1, 3):
        fig.update_xaxes(showgrid=True, gridcolor=GRID_COLOR, row=i, col=1)
        fig.update_yaxes(showgrid=True, gridcolor=GRID_COLOR, row=i, col=1)

    return fig


def create_confluence_gauge(score: float) -> go.Figure:
    color = SUCCESS if score >= 0.90 else WARNING if score >= 0.70 else DANGER

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score * 100,
        number=dict(suffix="%", font=dict(size=36, color=color, family="JetBrains Mono")),
        gauge=dict(
            axis=dict(range=[0, 100], tickcolor=TEXT_DIM, tickfont=dict(color=TEXT_DIM)),
            bar=dict(color=color),
            bgcolor=BG_PRIMARY,
            bordercolor=ACCENT_DIM,
            steps=[
                dict(range=[0, 70], color="rgba(255,51,102,0.1)"),
                dict(range=[70, 90], color="rgba(255,170,0,0.1)"),
                dict(range=[90, 100], color="rgba(0,255,136,0.1)"),
            ],
            threshold=dict(line=dict(color=ACCENT, width=3), thickness=0.8, value=90),
        ),
    ))

    fig.update_layout(
        paper_bgcolor=BG_CARD,
        plot_bgcolor=BG_PRIMARY,
        height=200,
        margin=dict(l=30, r=30, t=30, b=10),
        font=dict(family="JetBrains Mono", color=TEXT_DIM),
    )
    return fig


def format_log_entry(timestamp: str, level: str, message: str) -> str:
    cls_map = {"INFO": "log-info", "SUCCESS": "log-success", "WARNING": "log-warning", "ERROR": "log-danger"}
    cls = cls_map.get(level, "log-info")
    return f'<div class="log-entry {cls}"><span style="color:{TEXT_DIM}">[{timestamp}]</span> <span style="color:{ACCENT}">[{level}]</span> {message}</div>'


def load_shared_state() -> dict:
    state_file = Path(__file__).parent.parent / "data" / "system_state.json"
    if state_file.exists():
        try:
            with open(state_file) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {
        "balance": 10.0,
        "equity": 10.0,
        "profit": 0.0,
        "active_trades": 0,
        "total_trades": 0,
        "daily_pnl": 0.0,
        "equity_curve": [10.0],
        "signals": [],
        "logs": [],
        "agents": {
            "Trader Ultima": "IDLE",
            "Chart Analyzer": "IDLE",
            "News Scanner": "IDLE",
            "Code Auditor": "IDLE",
            "Voice Engine": "IDLE",
        },
        "last_signal": None,
        "confluence_score": 0.0,
    }


def main():
    st.set_page_config(
        page_title="J.A.R.V.I.S. V300 WAR ROOM",
        page_icon="🔮",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    inject_css()

    state = load_shared_state()

    # ── Sidebar ──────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown(f'<div class="war-room-title">J.A.R.V.I.S. V300</div>', unsafe_allow_html=True)
        st.markdown(f'<p style="color:{TEXT_DIM}; font-family: JetBrains Mono; font-size: 0.75rem;">OMNIPOTENCE PROTOCOL ACTIVE</p>', unsafe_allow_html=True)

        st.markdown("---")
        st.markdown(f'<p style="color:{ACCENT}; font-size: 0.8rem; letter-spacing: 2px;">AGENT STATUS</p>', unsafe_allow_html=True)

        agents_html = ""
        for name, status in state.get("agents", {}).items():
            agents_html += agent_status_row(name, status)
        st.markdown(agents_html, unsafe_allow_html=True)

        st.markdown("---")
        st.markdown(f'<p style="color:{ACCENT}; font-size: 0.8rem; letter-spacing: 2px;">SYSTEM INFO</p>', unsafe_allow_html=True)
        st.markdown(f"""
        <div style="font-family: JetBrains Mono; font-size: 0.75rem; color: {TEXT_DIM};">
            <p>Time: {datetime.now().strftime('%H:%M:%S')}</p>
            <p>Mode: SMC Scalper M1</p>
            <p>Symbol: EURUSD</p>
            <p>Risk: {1.0}% per trade</p>
        </div>
        """, unsafe_allow_html=True)

    # ── Header ───────────────────────────────────────────────────────────
    st.markdown(f'<div class="war-room-title">WAR ROOM — COMMAND CENTER</div>', unsafe_allow_html=True)

    # ── Top Metrics ──────────────────────────────────────────────────────
    cols = st.columns(5)

    balance = state.get("balance", 10.0)
    equity = state.get("equity", 10.0)
    profit = state.get("profit", 0.0)
    profit_color = SUCCESS if profit >= 0 else DANGER

    with cols[0]:
        st.markdown(metric_card("BALANCE", f"€{balance:.2f}", ACCENT), unsafe_allow_html=True)
    with cols[1]:
        st.markdown(metric_card("EQUITY", f"€{equity:.2f}", ACCENT), unsafe_allow_html=True)
    with cols[2]:
        st.markdown(metric_card("P&L TODAY", f"€{profit:+.2f}", profit_color), unsafe_allow_html=True)
    with cols[3]:
        st.markdown(metric_card("ACTIVE TRADES", str(state.get("active_trades", 0)), WARNING), unsafe_allow_html=True)
    with cols[4]:
        confluence = state.get("confluence_score", 0.0)
        conf_color = SUCCESS if confluence >= 0.90 else WARNING if confluence >= 0.70 else TEXT_DIM
        st.markdown(metric_card("CONFLUENCE", f"{confluence:.0%}", conf_color), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Main Charts ──────────────────────────────────────────────────────
    tab_chart, tab_equity, tab_signals, tab_logs = st.tabs(
        ["LIVE CHART", "EQUITY CURVE", "SIGNAL LOG", "SYSTEM LOG"]
    )

    with tab_chart:
        np.random.seed(42)
        n = 100
        base = 1.0850
        prices = [base]
        for _ in range(n - 1):
            prices.append(prices[-1] + np.random.normal(0, 0.0002))

        sim_df = pd.DataFrame({
            "open": prices,
            "high": [p + abs(np.random.normal(0, 0.0003)) for p in prices],
            "low": [p - abs(np.random.normal(0, 0.0003)) for p in prices],
            "close": [p + np.random.normal(0, 0.0001) for p in prices],
            "tick_volume": np.random.randint(50, 500, n),
        }, index=pd.date_range(end=datetime.now(), periods=n, freq="1min"))

        chart = create_candlestick_chart(sim_df, state.get("signals", []))
        st.plotly_chart(chart, use_container_width=True)

    with tab_equity:
        eq_data = state.get("equity_curve", [10.0])
        eq_chart = create_equity_chart(eq_data)
        st.plotly_chart(eq_chart, use_container_width=True)

        col_a, col_b, col_c = st.columns(3)
        if len(eq_data) > 1:
            total_return = ((eq_data[-1] - eq_data[0]) / eq_data[0]) * 100
            max_eq = max(eq_data)
            drawdown = ((max_eq - eq_data[-1]) / max_eq) * 100 if max_eq > 0 else 0
        else:
            total_return = 0.0
            drawdown = 0.0

        with col_a:
            ret_color = SUCCESS if total_return >= 0 else DANGER
            st.markdown(metric_card("TOTAL RETURN", f"{total_return:+.1f}%", ret_color), unsafe_allow_html=True)
        with col_b:
            st.markdown(metric_card("MAX DRAWDOWN", f"{drawdown:.1f}%", DANGER), unsafe_allow_html=True)
        with col_c:
            st.markdown(metric_card("TRADES", str(state.get("total_trades", 0)), ACCENT), unsafe_allow_html=True)

    with tab_signals:
        last_sig = state.get("last_signal")
        if last_sig:
            sig_cols = st.columns([1, 2, 2])
            with sig_cols[0]:
                direction = last_sig.get("direction", "—")
                st.markdown(signal_badge(direction), unsafe_allow_html=True)
            with sig_cols[1]:
                st.markdown(f"""
                <div style="font-family: JetBrains Mono; font-size: 0.85rem; color: {TEXT_PRIMARY};">
                    Entry: {last_sig.get('entry', '—')}<br>
                    SL: {last_sig.get('sl', '—')}<br>
                    TP: {last_sig.get('tp', '—')}
                </div>
                """, unsafe_allow_html=True)
            with sig_cols[2]:
                score = last_sig.get("confluence", 0)
                gauge = create_confluence_gauge(score)
                st.plotly_chart(gauge, use_container_width=True)

            if last_sig.get("reasons"):
                st.markdown(f'<p style="color: {TEXT_DIM}; font-size: 0.8rem; margin-top: 10px;">Confluences:</p>', unsafe_allow_html=True)
                for r in last_sig["reasons"]:
                    st.markdown(f'<div class="log-entry log-info">{r}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<p style="color: {TEXT_DIM}; font-family: JetBrains Mono; text-align: center; padding: 40px;">AWAITING SIGNAL...</p>', unsafe_allow_html=True)

    with tab_logs:
        logs = state.get("logs", [])
        if logs:
            logs_html = ""
            for log in logs[-50:]:
                logs_html += format_log_entry(
                    log.get("time", "—"),
                    log.get("level", "INFO"),
                    log.get("msg", ""),
                )
            st.markdown(logs_html, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div style="text-align: center; padding: 40px; color: {TEXT_DIM}; font-family: JetBrains Mono;">
                {format_log_entry(datetime.now().strftime('%H:%M:%S'), 'INFO', 'J.A.R.V.I.S. V300 initialized. Awaiting commands, Sir.')}
                {format_log_entry(datetime.now().strftime('%H:%M:%S'), 'INFO', 'SMC Analyzer online. Scanning M1 for setups...')}
                {format_log_entry(datetime.now().strftime('%H:%M:%S'), 'INFO', 'Risk Manager active. Max daily loss: 5%')}
            </div>
            """, unsafe_allow_html=True)

    # ── Auto Refresh ─────────────────────────────────────────────────────
    time.sleep(2)
    st.rerun()


if __name__ == "__main__":
    main()
