from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

try:
    from streamlit_autorefresh import st_autorefresh
except Exception:  # pragma: no cover - optional dependency
    st_autorefresh = None


BASE_DIR = Path(__file__).resolve().parent
RUNTIME_DIR = BASE_DIR / "runtime"
STATE_FILE = RUNTIME_DIR / "jarvis_state.json"
TRADING_FILE = RUNTIME_DIR / "trading_snapshot.json"
SCREEN_FILE = RUNTIME_DIR / "screen_snapshot.json"
AUDIT_FILE = RUNTIME_DIR / "security_audit.json"


def load_json(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def run_command(command: str) -> tuple[bool, str]:
    try:
        result = subprocess.run(
            [sys.executable, str(BASE_DIR / "jarvis.py"), "--command", command],
            cwd=BASE_DIR,
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
        output = result.stdout.strip() or result.stderr.strip()
        return result.returncode == 0, output
    except Exception as exc:
        return False, str(exc)


def war_room_css() -> None:
    st.markdown(
        """
        <style>
            .stApp {
                background: radial-gradient(circle at top, #08111f 0%, #03060b 45%, #000000 100%);
                color: #d8f6ff;
            }
            .block-container {
                padding-top: 1.5rem;
                padding-bottom: 2rem;
            }
            .jarvis-card {
                background: rgba(5, 18, 33, 0.92);
                border: 1px solid rgba(35, 197, 255, 0.35);
                border-radius: 18px;
                box-shadow: 0 0 20px rgba(0, 179, 255, 0.14);
                padding: 1rem 1.25rem;
                margin-bottom: 1rem;
            }
            .jarvis-title {
                color: #7be8ff;
                letter-spacing: 0.18rem;
                text-transform: uppercase;
                font-weight: 700;
            }
            div[data-testid="metric-container"] {
                background: rgba(5, 18, 33, 0.92);
                border: 1px solid rgba(35, 197, 255, 0.35);
                padding: 0.75rem;
                border-radius: 16px;
                box-shadow: 0 0 16px rgba(0, 179, 255, 0.1);
            }
            .log-box {
                background: rgba(1, 8, 16, 0.95);
                border: 1px solid rgba(35, 197, 255, 0.25);
                border-radius: 12px;
                padding: 0.85rem;
                font-family: Consolas, monospace;
                font-size: 0.82rem;
                white-space: pre-wrap;
                min-height: 260px;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def build_equity_chart(trading: dict[str, Any]) -> go.Figure:
    history = pd.DataFrame(trading.get("equity_curve", []))
    figure = go.Figure()
    if not history.empty:
        history["time"] = pd.to_datetime(history["time"])
        figure.add_trace(
            go.Scatter(
                x=history["time"],
                y=history["equity"],
                mode="lines+markers",
                line={"color": "#19d5ff", "width": 3},
                marker={"size": 6, "color": "#9ef6ff"},
                fill="tozeroy",
                fillcolor="rgba(25,213,255,0.12)",
                name="Equity",
            )
        )
    figure.update_layout(
        margin={"l": 10, "r": 10, "t": 20, "b": 10},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(5,18,33,0.85)",
        font={"color": "#d8f6ff"},
        xaxis={"showgrid": False},
        yaxis={"gridcolor": "rgba(123,232,255,0.12)"},
    )
    return figure


def build_signal_chart(trading: dict[str, Any]) -> go.Figure:
    signals = pd.DataFrame(trading.get("signals", []))
    figure = go.Figure()
    if not signals.empty:
        colors = ["#11f7a0" if side == "BUY" else "#ff5874" if side == "SELL" else "#7be8ff" for side in signals["side"]]
        figure.add_trace(
            go.Bar(
                x=signals["symbol"],
                y=signals["confluence"],
                marker={"color": colors},
                text=signals["side"],
                textposition="outside",
                name="Confluence",
            )
        )
    figure.update_layout(
        margin={"l": 10, "r": 10, "t": 20, "b": 10},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(5,18,33,0.85)",
        font={"color": "#d8f6ff"},
        yaxis={"range": [0, 100], "gridcolor": "rgba(123,232,255,0.12)"},
        xaxis={"showgrid": False},
    )
    return figure


def render_logs(lines: list[str]) -> None:
    st.markdown('<div class="jarvis-card"><div class="jarvis-title">Status Logs</div>', unsafe_allow_html=True)
    content = "\n".join(lines[-18:]) if lines else "No logs yet."
    st.markdown(f'<div class="log-box">{content}</div></div>', unsafe_allow_html=True)


def render_sidebar() -> None:
    st.sidebar.markdown("## Command Uplink")
    command = st.sidebar.text_input("Manual command", value="status")
    if st.sidebar.button("Execute command", use_container_width=True):
        ok, output = run_command(command)
        if ok:
            st.sidebar.success(output)
        else:
            st.sidebar.error(output)

    if st.sidebar.button("Run trading cycle", use_container_width=True):
        ok, output = run_command("trade cycle")
        st.sidebar.success(output) if ok else st.sidebar.error(output)

    if st.sidebar.button("Run security audit", use_container_width=True):
        ok, output = run_command(f"audit {BASE_DIR}")
        st.sidebar.success(output) if ok else st.sidebar.error(output)

    if st.sidebar.button("Scan screen", use_container_width=True):
        ok, output = run_command("scan screen")
        st.sidebar.success(output) if ok else st.sidebar.error(output)

    st.sidebar.caption("Operator note: live trading remains gated by JARVIS_ENABLE_LIVE_TRADING=1.")


def main() -> None:
    st.set_page_config(page_title="JARVIS War Room", layout="wide", initial_sidebar_state="expanded")
    war_room_css()
    if st_autorefresh:
        st_autorefresh(interval=5_000, key="jarvis_refresh")

    render_sidebar()

    state = load_json(STATE_FILE, {})
    trading = load_json(TRADING_FILE, {})
    screen = load_json(SCREEN_FILE, {})
    audit = load_json(AUDIT_FILE, {})

    st.markdown('<div class="jarvis-title" style="font-size:2rem;">J.A.R.V.I.S. War Room</div>', unsafe_allow_html=True)
    st.caption("Integrated operator console for strategy, coding, audit and desktop telemetry.")

    col_a, col_b, col_c, col_d = st.columns(4)
    col_a.metric("Mode", trading.get("mode", "paper").upper())
    col_b.metric("Balance", f"{trading.get('balance', 0):,.2f}")
    col_c.metric("Equity", f"{trading.get('equity', 0):,.2f}")
    col_d.metric("Open Positions", len(trading.get("positions", [])))

    top_left, top_right = st.columns([1.6, 1.0])
    with top_left:
        st.markdown('<div class="jarvis-card"><div class="jarvis-title">Equity Matrix</div></div>', unsafe_allow_html=True)
        st.plotly_chart(build_equity_chart(trading), use_container_width=True)
    with top_right:
        st.markdown('<div class="jarvis-card"><div class="jarvis-title">Agent Signals</div></div>', unsafe_allow_html=True)
        st.plotly_chart(build_signal_chart(trading), use_container_width=True)

    lower_left, lower_mid, lower_right = st.columns([1.0, 1.0, 1.2])
    with lower_left:
        st.markdown('<div class="jarvis-card"><div class="jarvis-title">Trading Book</div>', unsafe_allow_html=True)
        positions = pd.DataFrame(trading.get("positions", []))
        if positions.empty:
            st.info("No open positions.")
        else:
            st.dataframe(positions, use_container_width=True, hide_index=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with lower_mid:
        st.markdown('<div class="jarvis-card"><div class="jarvis-title">Screen Intelligence</div>', unsafe_allow_html=True)
        if screen:
            st.json(screen["summary"])
            if screen.get("image_path"):
                image_path = Path(screen["image_path"])
                if image_path.exists():
                    st.image(str(image_path), use_container_width=True)
        else:
            st.info("No screen snapshot available.")
        st.markdown("</div>", unsafe_allow_html=True)

    with lower_right:
        st.markdown('<div class="jarvis-card"><div class="jarvis-title">Audit Pulse</div>', unsafe_allow_html=True)
        if audit:
            st.metric("Findings", audit.get("finding_count", 0))
            findings = pd.DataFrame(audit.get("findings", []))
            if findings.empty:
                st.success("No findings in last audit.")
            else:
                st.dataframe(findings.head(12), use_container_width=True, hide_index=True)
        else:
            st.info("No audit report available.")
        st.markdown("</div>", unsafe_allow_html=True)

    render_logs(state.get("logs", []) + trading.get("logs", []))

    st.markdown('<div class="jarvis-card"><div class="jarvis-title">Generated Apps</div>', unsafe_allow_html=True)
    generated_apps = state.get("generated_apps", [])
    if generated_apps:
        app_frame = pd.DataFrame(
            [
                {
                    "name": item["app_name"],
                    "path": item["app_path"],
                    "files": len(item["generated_files"]),
                    "generated_at": item["generated_at"],
                }
                for item in generated_apps
            ]
        )
        st.dataframe(app_frame, use_container_width=True, hide_index=True)
    else:
        st.info("No apps generated yet.")
    st.markdown("</div>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
