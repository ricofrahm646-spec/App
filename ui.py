"""
Streamlit 'War Room' dashboard: equity, agent signals, logs.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from config import LOGS_DIR, ROOT

st.set_page_config(page_title="J.A.R.V.I.S. War Room", layout="wide", initial_sidebar_state="expanded")

WAR_ROOM_CSS = """
<style>
    .stApp { background-color: #050508; color: #e8f6ff; }
    header[data-testid="stHeader"] { background: transparent; }
    div[data-testid="stToolbar"] { visibility: hidden; height: 0; }
    .block-container { padding-top: 1.2rem; }
    h1, h2, h3 { color: #5ecbff !important; letter-spacing: 0.04em; }
    .metric-card {
        border: 1px solid #1b2f44;
        border-radius: 10px;
        padding: 14px 16px;
        background: linear-gradient(145deg, #0a0f18, #0d1624);
        box-shadow: 0 0 18px rgba(0, 198, 255, 0.08);
    }
    .neon { color: #5ecbff; text-shadow: 0 0 8px rgba(94, 203, 255, 0.55); }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        background-color: #0c121c;
        border: 1px solid #1b2f44;
        color: #9ad8ff;
    }
</style>
"""


def load_jsonl(path: Path, limit: int = 2000) -> pd.DataFrame:
    if not path.is_file():
        return pd.DataFrame()
    rows: list[dict] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    return df.tail(limit)


def main() -> None:
    st.markdown(WAR_ROOM_CSS, unsafe_allow_html=True)
    st.markdown("# <span class='neon'>J.A.R.V.I.S. // WAR ROOM</span>", unsafe_allow_html=True)
    st.caption("Operational view — not financial advice. Live metrics depend on local modules.")

    equity_path = LOGS_DIR / "equity.jsonl"
    signal_path = LOGS_DIR / "signals.jsonl"
    system_log = LOGS_DIR / "system.log"

    eq_df = load_jsonl(equity_path)
    sig_df = load_jsonl(signal_path)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown("<div class='metric-card'><b>STATUS</b><br/>ONLINE</div>", unsafe_allow_html=True)
    with c2:
        last_eq = float(eq_df["equity"].iloc[-1]) if not eq_df.empty and "equity" in eq_df.columns else None
        st.markdown(
            f"<div class='metric-card'><b>EQUITY (LAST)</b><br/>{last_eq or '—'}</div>",
            unsafe_allow_html=True,
        )
    with c3:
        conf = float(sig_df["confluence"].iloc[-1]) if not sig_df.empty and "confluence" in sig_df.columns else None
        st.markdown(
            f"<div class='metric-card'><b>LAST CONFLUENCE</b><br/>{conf if conf is not None else '—'}</div>",
            unsafe_allow_html=True,
        )
    with c4:
        st.markdown(
            f"<div class='metric-card'><b>ROOT</b><br/><code>{ROOT}</code></div>",
            unsafe_allow_html=True,
        )

    tab_eq, tab_sig, tab_log, tab_audit = st.tabs(["Equity", "Agent Signals", "Logs", "Security Audit"])

    with tab_eq:
        if eq_df.empty or "equity" not in eq_df.columns:
            st.info("No equity samples yet. Run `trader_ultimate` connected to MT5 to populate `logs/equity.jsonl`.")
        else:
            eq_df["ts"] = pd.to_datetime(eq_df["ts"], utc=True, errors="coerce")
            fig = go.Figure()
            fig.add_trace(
                go.Scatter(
                    x=eq_df["ts"],
                    y=eq_df["equity"],
                    mode="lines",
                    line=dict(color="#5ecbff", width=2),
                    fill="tozeroy",
                    fillcolor="rgba(94,203,255,0.08)",
                )
            )
            fig.update_layout(
                template="plotly_dark",
                paper_bgcolor="#050508",
                plot_bgcolor="#0a0f18",
                font=dict(color="#cde9ff"),
                margin=dict(l=10, r=10, t=40, b=10),
                title="Equity (logged)",
            )
            st.plotly_chart(fig, use_container_width=True)

    with tab_sig:
        if sig_df.empty:
            st.info("No signals logged yet.")
        else:
            show = sig_df.tail(200).copy()
            if "ts" in show.columns:
                show["ts"] = pd.to_datetime(show["ts"], utc=True, errors="coerce")
            st.dataframe(show, use_container_width=True, height=420)

    with tab_log:
        if system_log.is_file():
            tail = "".join(system_log.read_text(encoding="utf-8", errors="ignore").splitlines(True)[-400:])
            st.code(tail or "(empty)", language="text")
        else:
            st.write("No system.log — redirect stdout from `jarvis.py` to `logs/system.log` if desired.")

    with tab_audit:
        if st.button("Run static audit on /apps"):
            from ghost_security import audit_apps

            issues = audit_apps()
            st.json(issues or {"status": "clean"})

    st.markdown("---")
    st.write(
        datetime.now(timezone.utc).strftime("UTC %Y-%m-%d %H:%M:%S"),
        "| Configure MT5 via `.env`. Respect broker rules and local law.",
    )


if __name__ == "__main__":
    main()
