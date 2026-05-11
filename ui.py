from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from jarvis import JarvisMasterBrain


st.set_page_config(page_title="JARVIS V300 War Room", layout="wide")


def inject_theme() -> None:
    st.markdown(
        """
<style>
    .stApp {
        background: radial-gradient(circle at top right, #0b1a36 0%, #05070e 42%, #000000 100%);
        color: #d7ebff;
    }
    .war-title {
        font-size: 2.2rem;
        font-weight: 800;
        color: #8ed6ff;
        text-shadow: 0 0 18px rgba(0, 194, 255, 0.45);
        margin-bottom: 0.15rem;
    }
    .war-subtitle {
        color: #8ec5ff;
        opacity: 0.86;
        margin-bottom: 1.2rem;
    }
    .block-container {
        padding-top: 1rem;
    }
    .stMetric {
        background: rgba(2, 10, 22, 0.85);
        border: 1px solid rgba(31, 148, 255, 0.35);
        border-radius: 12px;
        padding: 12px;
        box-shadow: 0 0 22px rgba(0, 140, 255, 0.12);
    }
    div[data-baseweb="select"] > div {
        background: #060c18;
        border-color: #176eb6;
    }
    .stDataFrame, .stTable {
        border: 1px solid rgba(31, 148, 255, 0.35);
        border-radius: 10px;
    }
</style>
""",
        unsafe_allow_html=True,
    )


@st.cache_resource(show_spinner=False)
def get_brain(symbol: str, dry_run: bool) -> JarvisMasterBrain:
    brain = JarvisMasterBrain(symbol=symbol, dry_run=dry_run, voice_enabled=False)
    brain.boot()
    return brain


def to_dataframe(items: List[Dict[str, Any]]) -> pd.DataFrame:
    if not items:
        return pd.DataFrame()
    return pd.DataFrame(items)


def render_equity_chart(equity_data: List[Dict[str, Any]]) -> None:
    if not equity_data:
        st.info("No equity samples yet. Run a trading cycle.")
        return
    df = pd.DataFrame(equity_data)
    df["time"] = pd.to_datetime(df["time"], utc=True)
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df["time"],
            y=df["equity"],
            mode="lines+markers",
            line=dict(color="#00f5ff", width=3),
            marker=dict(size=5, color="#68d8ff"),
            name="Equity",
        )
    )
    fig.update_layout(
        template="plotly_dark",
        height=320,
        margin=dict(l=10, r=10, t=25, b=10),
        plot_bgcolor="rgba(0,0,0,0.2)",
        paper_bgcolor="rgba(0,0,0,0)",
        title="Equity Trajectory",
    )
    st.plotly_chart(fig, use_container_width=True)


def render_signal_chart(signal_data: List[Dict[str, Any]]) -> None:
    if not signal_data:
        st.info("No signals generated yet.")
        return
    df = pd.DataFrame(signal_data)
    df["time"] = pd.to_datetime(df["time"], utc=True)
    df["confidence"] = pd.to_numeric(df["confidence"], errors="coerce").fillna(0.0)
    colors = df["direction"].map({"long": "#00ffb7", "short": "#ff4f7f"}).fillna("#8ec5ff")

    fig = go.Figure(
        data=[
            go.Scatter(
                x=df["time"],
                y=df["confidence"],
                mode="markers+lines",
                marker=dict(size=10, color=colors),
                line=dict(width=2, color="#88b8ff"),
                text=df["reason"],
                name="Signal confidence",
            )
        ]
    )
    fig.update_layout(
        template="plotly_dark",
        height=320,
        margin=dict(l=10, r=10, t=25, b=10),
        plot_bgcolor="rgba(0,0,0,0.2)",
        paper_bgcolor="rgba(0,0,0,0)",
        title="Agent Signal Feed",
        yaxis_title="Confidence",
    )
    st.plotly_chart(fig, use_container_width=True)


def main() -> None:
    inject_theme()
    st.markdown('<div class="war-title">J.A.R.V.I.S V300 — OMNIPOTENCE WAR ROOM</div>', unsafe_allow_html=True)
    st.markdown('<div class="war-subtitle">Trading • Coding • Security • Vision • OS Control</div>', unsafe_allow_html=True)

    with st.sidebar:
        st.header("Mission Control")
        symbol = st.text_input("Trading Symbol", value=st.session_state.get("symbol", "EURUSD")).upper().strip() or "EURUSD"
        dry_run = st.toggle("Dry-run mode", value=st.session_state.get("dry_run", True))
        if st.button("Reinitialize Core"):
            st.cache_resource.clear()
        st.session_state["symbol"] = symbol
        st.session_state["dry_run"] = dry_run

    brain = get_brain(symbol=symbol, dry_run=dry_run)
    snapshot = brain.status()

    col_a, col_b, col_c, col_d = st.columns(4)
    col_a.metric("Balance", f"{snapshot['trading']['balance']:.2f}")
    col_b.metric("MT5 Connected", "YES" if snapshot["trading"]["connected"] else "NO")
    col_c.metric("Mode", "DRY-RUN" if snapshot["trading"]["dry_run"] else "LIVE")
    col_d.metric("Logs", f"{len(snapshot['trading']['status'])}")

    action_col_1, action_col_2, action_col_3 = st.columns(3)
    with action_col_1:
        if st.button("Execute Trading Cycle", use_container_width=True):
            result = brain.trading_cycle()
            st.session_state["last_trade_result"] = result
    with action_col_2:
        if st.button("Run Vision Sweep", use_container_width=True):
            result = brain.vision_cycle()
            st.session_state["last_vision_result"] = result
    with action_col_3:
        if st.button("Run Security Audit", use_container_width=True):
            result = brain.security_audit(target=".")
            st.session_state["last_security_result"] = result

    st.divider()

    c1, c2 = st.columns(2)
    with c1:
        render_equity_chart(snapshot["trading"]["equity_curve"])
    with c2:
        render_signal_chart(snapshot["trading"]["signals"])

    st.subheader("Status Log")
    status_df = to_dataframe(snapshot["trading"]["status"])
    if status_df.empty:
        st.info("No status entries available.")
    else:
        st.dataframe(status_df.iloc[::-1].head(120), use_container_width=True, height=300)

    st.subheader("Ops Console")
    ops1, ops2 = st.columns(2)
    with ops1:
        st.markdown("#### Ghost Research")
        ghost_url = st.text_input("URL", value="https://www.reuters.com/markets/")
        if st.button("Collect Digest", use_container_width=True):
            try:
                digest = brain.ghost_digest(ghost_url)
                st.session_state["ghost_digest"] = digest
            except Exception as exc:
                st.error(f"Ghost digest failed: {exc}")
        if "ghost_digest" in st.session_state:
            st.json(st.session_state["ghost_digest"])

    with ops2:
        st.markdown("#### Coding Core")
        app_name = st.text_input("App name", value="alpha-sentinel")
        app_type = st.selectbox("App type", options=["cli", "streamlit", "fastapi"], index=0)
        app_desc = st.text_input("Description", value="Generated by JARVIS Coding Core")
        app_features = st.text_area("Features (one per line)", value="signal parsing\nstructured logs\nsafety checks")
        if st.button("Generate App in /apps", use_container_width=True):
            features = [line.strip() for line in app_features.splitlines() if line.strip()]
            generated = brain.create_app(name=app_name, app_type=app_type, description=app_desc, features=features)
            st.session_state["generated_app"] = generated
        if "generated_app" in st.session_state:
            st.json(st.session_state["generated_app"])

    st.subheader("Latest Action Outputs")
    output_cols = st.columns(3)
    output_cols[0].markdown("#### Trading")
    output_cols[0].json(st.session_state.get("last_trade_result", {"status": "idle"}))
    output_cols[1].markdown("#### Vision")
    output_cols[1].json(st.session_state.get("last_vision_result", {"status": "idle"}))
    output_cols[2].markdown("#### Security")
    output_cols[2].json(st.session_state.get("last_security_result", {"status": "idle"}))

    st.caption(f"UTC: {datetime.now(timezone.utc).isoformat()}")


if __name__ == "__main__":
    main()
