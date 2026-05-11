"""JARVIS War Room dashboard."""

from __future__ import annotations

import asyncio
from datetime import datetime

import streamlit as st

from memory.memory import MemoryStore
from trading.engine import TradingEngine


st.set_page_config(page_title="JARVIS War Room", page_icon=":robot_face:", layout="wide")
st.markdown(
    """
    <style>
      .stApp { background-color: #05070d; color: #8fe8ff; }
      .stMetric { background-color: #0b1220; border: 1px solid #10b6ff33; border-radius: 12px; padding: 8px; }
      .block-container { padding-top: 1.2rem; }
      h1, h2, h3 { color: #5ed9ff; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("J.A.R.V.I.S. War Room")
st.caption(f"Operational snapshot: {datetime.utcnow().isoformat(timespec='seconds')}Z")


@st.cache_resource(show_spinner=False)
def get_memory() -> MemoryStore:
    return MemoryStore()


@st.cache_resource(show_spinner=False)
def get_engine() -> TradingEngine:
    return TradingEngine(memory=get_memory())


memory = get_memory()
engine = get_engine()

left, right = st.columns([1, 1])
with left:
    st.subheader("Trading Simulation")
    cycles = st.slider("Improvement cycles", min_value=1, max_value=10, value=3)
    seed = st.number_input("Market seed", min_value=1, max_value=100000, value=42)
    if st.button("Run simulation", use_container_width=True):
        report = asyncio.run(engine.run_improvement_cycle(cycles=cycles, seed=int(seed)))
        st.success("Simulation completed.")
        st.json(
            {
                "top_strategy": report.top_strategy,
                "final_strategy_count": report.final_strategy_count,
                "improvements": report.improvements[:5],
            }
        )

with right:
    st.subheader("Memory Snapshot")
    if st.button("Refresh memory", use_container_width=True):
        snapshot = asyncio.run(memory.snapshot())
        st.json(
            {
                "tasks": len(snapshot["tasks"]),
                "results": len(snapshot["results"]),
                "events": len(snapshot["events"]),
                "knowledge": len(snapshot["knowledge"]),
                "improvements": len(snapshot["improvements"]),
            }
        )
        if snapshot["knowledge"]:
            st.markdown("#### Latest knowledge entries")
            st.json(snapshot["knowledge"][-3:])

