"""
JARVIS Universal Creator adaptive Streamlit shell.

Run with:
    streamlit run ui/main_shell.py
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core.compiler import ArchitectCompiler, BuildResult
from core.os_bridge import OSBridge
from core.processor import MultiFormatProcessor, SourceBundle
from ghost_security import SecurityAuditor
from trader.scalper import AggressiveScalingScalper, ScalingState


SHELL_CSS = """
<style>
.stApp {
    background: radial-gradient(circle at top right, #071426 0%, #01030a 45%, #000000 100%);
}
.god-console textarea {
    border: 1px solid #00d4ff !important;
}
.jarvis-shell-title {
    font-size: 2.4rem;
    color: #e0faff;
    letter-spacing: .16rem;
    font-weight: 800;
    text-shadow: 0 0 18px #00aaff;
}
.jarvis-panel {
    border: 1px solid #0ea5ff66;
    border-radius: 16px;
    padding: 1rem;
    background: #020916bf;
}
</style>
"""


def init_state() -> None:
    st.session_state.setdefault("mode", "creator")
    st.session_state.setdefault("logs", [])
    st.session_state.setdefault("last_build", None)
    st.session_state.setdefault("last_scalper", None)
    st.session_state.setdefault("last_sources", None)


def log(message: str) -> None:
    st.session_state.logs.insert(0, message)
    st.session_state.logs = st.session_state.logs[:80]


def render_header() -> None:
    st.set_page_config(page_title="JARVIS Universal Creator", page_icon="J", layout="wide")
    st.markdown(SHELL_CSS, unsafe_allow_html=True)
    st.markdown('<div class="jarvis-shell-title">J.A.R.V.I.S. UNIVERSAL CREATOR CORE</div>', unsafe_allow_html=True)
    st.caption("Architect Engine | Multi-Format Processor | OS Bridge | Scalper Foundation | Security Audit")


def process_uploads(files: list[Any]) -> SourceBundle | None:
    if not files:
        return None
    upload_dir = Path("uploads")
    upload_dir.mkdir(exist_ok=True)
    paths: list[Path] = []
    for uploaded in files:
        target = upload_dir / uploaded.name
        target.write_bytes(uploaded.getbuffer())
        paths.append(target)
    bundle = MultiFormatProcessor().process_many(paths)
    st.session_state.last_sources = bundle
    log(f"Processed {len(bundle.documents)} PDF(s) and {len(bundle.images)} image(s).")
    return bundle


def execute_command(command: str, bundle: SourceBundle | None) -> dict[str, Any]:
    normalized = command.strip().lower()
    compiler = ArchitectCompiler()
    if not command.strip():
        return {"error": "No command supplied"}
    if any(keyword in normalized for keyword in ("trade", "scalp", "mt5", "trading")) and "build" not in normalized:
        scalper = AggressiveScalingScalper()
        snapshot = scalper.scan_once()
        st.session_state.mode = "trading"
        st.session_state.last_scalper = snapshot
        log(f"Scalper scan: {snapshot.get('status')} - {snapshot.get('reason', 'processed')}")
        return {"scalper": snapshot}
    if any(keyword in normalized for keyword in ("audit", "security scan", "scan code")):
        findings = SecurityAuditor(["apps", "generated_projects", "."]).scan()
        st.session_state.mode = "audit"
        log(f"Security audit completed with {len(findings)} findings.")
        return {"findings": findings}
    if normalized.startswith("pip install "):
        packages = command.split()[2:]
        result = OSBridge().pip_install(packages)
        st.session_state.mode = "terminal"
        log(f"Pip install finished with exit code {result.returncode}.")
        return {"command_result": result}

    source_text = bundle.text_context if bundle is not None else ""
    result = compiler.compile_request(command, source_text=source_text)
    st.session_state.mode = result.blueprint.kind
    st.session_state.last_build = result
    log(f"Built {result.blueprint.kind}: {result.root}")
    return {"build": result}


def render_build(result: BuildResult | None) -> None:
    if result is None:
        st.info("No project generated yet. Use the God-Mode console, Sir.")
        return
    st.subheader("Architect Build Output")
    st.success(f"Project ready: {result.root}")
    st.json(result.blueprint.manifest())
    st.write("Written files")
    st.dataframe(pd.DataFrame({"file": [str(path) for path in result.written_files]}), use_container_width=True)
    if result.audit_findings:
        st.warning(f"{len(result.audit_findings)} audit finding(s)")
        st.dataframe(pd.DataFrame([finding.__dict__ for finding in result.audit_findings]), use_container_width=True)
    else:
        st.success("Security audit clean.")


def render_trading(snapshot: dict[str, Any] | None) -> None:
    st.subheader("Aggressive Scaling Module")
    if snapshot is None:
        st.info("Run a scalper command to populate trading telemetry.")
        return
    state = snapshot.get("scaling_state")
    cols = st.columns(4)
    cols[0].metric("Status", str(snapshot.get("status", "idle")).upper())
    cols[1].metric("Live Trading", str(snapshot.get("live_trading", False)).upper())
    if isinstance(state, ScalingState):
        cols[2].metric("Progress", f"{state.progress:.1%}")
        cols[3].metric("Drawdown", f"{state.drawdown:.1%}")
        fig = go.Figure(
            go.Indicator(
                mode="gauge+number",
                value=state.current_equity,
                title={"text": "Equity Goal"},
                gauge={"axis": {"range": [state.plan.starting_equity, state.plan.target_equity]}},
            )
        )
        fig.update_layout(template="plotly_dark", height=320)
        st.plotly_chart(fig, use_container_width=True)
    st.json(_jsonable(snapshot))


def render_audit() -> None:
    st.subheader("Code Audit")
    findings = SecurityAuditor(["apps", "generated_projects", "."]).scan()
    if not findings:
        st.success("No audit findings.")
        return
    st.dataframe(pd.DataFrame([finding.__dict__ for finding in findings]), use_container_width=True)


def render_sources(bundle: SourceBundle | None) -> None:
    st.subheader("Multi-Format Processor")
    if bundle is None:
        st.info("Upload PDFs or images to extract project context.")
        return
    st.metric("PDFs", len(bundle.documents))
    st.metric("Images", len(bundle.images))
    with st.expander("Extracted Context"):
        st.text(bundle.text_context or "No extractable text.")


def _jsonable(value: Any) -> Any:
    if hasattr(value, "__dataclass_fields__"):
        return {key: _jsonable(getattr(value, key)) for key in value.__dataclass_fields__}
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def main() -> None:
    init_state()
    render_header()
    with st.sidebar:
        st.header("God-Mode Inputs")
        uploads = st.file_uploader("PDFs / Images", accept_multiple_files=True)
        bundle = process_uploads(uploads) if uploads else st.session_state.last_sources
        st.caption("Terminal/pip actions require explicit environment opt-in.")
        st.divider()
        selected = st.radio("View", ["Adaptive", "Creator", "Trading", "Processor", "Audit", "Logs"])

    command = st.text_area(
        "God-Mode Console",
        value="Jarvis, baue mir eine Streamlit App fuer meine Strategie",
        height=110,
        help="Examples: Jarvis, baue mir eine Trading-App; scalper scan; audit code",
    )
    if st.button("Execute Command", type="primary"):
        result = execute_command(command, bundle)
        st.json(_jsonable(result))

    active = selected.lower()
    if active == "adaptive":
        active = str(st.session_state.mode).lower()
    if active in {"creator", "web_app", "script", "documentation", "defensive_security", "trading_bot"}:
        render_build(st.session_state.last_build)
    elif active == "trading":
        render_trading(st.session_state.last_scalper)
    elif active == "processor":
        render_sources(bundle)
    elif active == "audit":
        render_audit()
    else:
        st.subheader("System Logs")
        for line in st.session_state.logs:
            st.code(line)


if __name__ == "__main__":
    main()
