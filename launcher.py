"""Entry point for JARVIS AI OS."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
from typing import Any

from agents import (
    AnalysisAgent,
    CodingAgent,
    MemoryAgent,
    ResearchAgent,
    TaskPlannerAgent,
    WebResearchAgent,
)
from agents.trading import (
    ArbitrageBotAgent,
    GoldScalperProAgent,
    LiquiditySweeperAgent,
    NewsReactorAgent,
    OrderflowMasterAgent,
    PortfolioAllocatorAgent,
    RiskCommanderAgent,
    SessionSniperAgent,
    TrendPulseAIAgent,
    VolatilityGuardianAgent,
)
from agents.trading.mt5_gateway import MT5Gateway
from controller import AppControlInterface
from core.orchestrator import Orchestrator, OrchestratorResponse
from core.safety import KillSwitch
from tools.search_tool import SearchTool


def configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


async def build_orchestrator() -> Orchestrator:
    orchestrator = Orchestrator()
    await orchestrator.setup()
    kill_switch = KillSwitch()
    search_tool = SearchTool(workspace_root=os.getcwd())
    gateway = MT5Gateway(allow_live_orders=False, kill_switch=kill_switch)

    await orchestrator.register_agents(
        [
            ResearchAgent(orchestrator.event_bus, orchestrator.memory),
            CodingAgent(orchestrator.event_bus, orchestrator.memory),
            AnalysisAgent(orchestrator.event_bus, orchestrator.memory),
            WebResearchAgent(
                orchestrator.event_bus,
                orchestrator.memory,
                search_tool=search_tool,
            ),
            TaskPlannerAgent(orchestrator.event_bus, orchestrator.memory),
            MemoryAgent(orchestrator.event_bus, orchestrator.memory),
            GoldScalperProAgent(orchestrator.event_bus, orchestrator.memory, gateway),
            RiskCommanderAgent(orchestrator.event_bus, orchestrator.memory, gateway),
            LiquiditySweeperAgent(orchestrator.event_bus, orchestrator.memory, gateway),
            NewsReactorAgent(
                orchestrator.event_bus,
                orchestrator.memory,
                gateway,
                search_tool=search_tool,
            ),
            OrderflowMasterAgent(orchestrator.event_bus, orchestrator.memory, gateway),
            ArbitrageBotAgent(orchestrator.event_bus, orchestrator.memory, gateway),
            SessionSniperAgent(orchestrator.event_bus, orchestrator.memory, gateway),
            VolatilityGuardianAgent(orchestrator.event_bus, orchestrator.memory, gateway),
            TrendPulseAIAgent(orchestrator.event_bus, orchestrator.memory, gateway),
            PortfolioAllocatorAgent(orchestrator.event_bus, orchestrator.memory, gateway),
        ]
    )
    orchestrator.app_controller = AppControlInterface(kill_switch=kill_switch)  # type: ignore[attr-defined]
    return orchestrator


def format_response(response: OrchestratorResponse) -> dict[str, Any]:
    return {
        "task": response.task,
        "selected_agent": response.selected_agent,
        "planner": {
            "confidence": response.planner_confidence,
            "reasoning": response.planner_reasoning,
        },
        "correlation_id": response.correlation_id,
        "result": response.result,
    }


async def run_single_task(orchestrator: Orchestrator, task: str, as_json: bool) -> None:
    if _is_control_command(task):
        control = await orchestrator.app_controller.execute(task)  # type: ignore[attr-defined]
        payload = {
            "task": task,
            "selected_agent": "AppControlInterface",
            "planner": {"confidence": 1.0, "reasoning": "Direct control command route."},
            "result": {"status": "success" if control.ok else "error", "output": control.details},
        }
        print(json.dumps(payload, indent=2) if as_json else json.dumps(payload["result"]["output"], indent=2))
        return

    response = await orchestrator.process_task(task)
    payload = format_response(response)
    if as_json:
        print(json.dumps(payload, indent=2))
        return
    print(f"Agent: {payload['selected_agent']}")
    print(f"Task: {payload['task']}")
    print(f"Reasoning: {payload['planner']['reasoning']}")
    print("Output:")
    print(json.dumps(payload["result"]["output"], indent=2))


def _is_control_command(task: str) -> bool:
    lowered = task.strip().lower()
    control_tokens = ("open ", "close ", "type ", "press ", "jarvis, abbruch", "jarvis abbruch", "abbruch")
    return any(lowered.startswith(token) for token in control_tokens)


async def interactive_loop(orchestrator: Orchestrator, as_json: bool) -> None:
    print("JARVIS AI OS interactive mode. Type 'exit' or 'quit' to stop.")
    while True:
        task = (await asyncio.to_thread(input, "\nJARVIS> ")).strip()
        if not task:
            continue
        if task.lower() in {"exit", "quit"}:
            print("Shutting down JARVIS AI OS.")
            break
        await run_single_task(orchestrator, task, as_json=as_json)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="JARVIS AI OS launcher")
    parser.add_argument(
        "--task",
        type=str,
        help="Run a single task and exit",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Render output as JSON",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    configure_logging(verbose=args.verbose)
    orchestrator = await build_orchestrator()
    if args.task:
        await run_single_task(orchestrator, task=args.task, as_json=args.json)
        return
    await interactive_loop(orchestrator, as_json=args.json)


if __name__ == "__main__":
    asyncio.run(main())

