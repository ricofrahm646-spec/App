"""
Aggressive Scaling Scalper foundation.

Builds on TradingUltima and frames the 10 EUR to 100 EUR objective as a tracked
goal with hard risk controls. Live orders still require JARVIS_LIVE_TRADING=1.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from trader_ultimate import ExecutionMode, TradeConfig, TradingUltima


@dataclass(frozen=True)
class ScalingPlan:
    starting_equity: float = 10.0
    target_equity: float = 100.0
    max_risk_per_trade: float = 0.015
    min_confluence: float = 0.90
    min_risk_reward: float = 1.5
    max_daily_drawdown: float = 0.20

    @property
    def target_multiple(self) -> float:
        return self.target_equity / self.starting_equity


@dataclass
class ScalingState:
    plan: ScalingPlan
    current_equity: float
    peak_equity: float
    trades_taken: int = 0
    blocked_reason: str = ""
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def progress(self) -> float:
        span = self.plan.target_equity - self.plan.starting_equity
        if span <= 0:
            return 1.0
        return max(0.0, min(1.0, (self.current_equity - self.plan.starting_equity) / span))

    @property
    def drawdown(self) -> float:
        if self.peak_equity <= 0:
            return 0.0
        return max(0.0, (self.peak_equity - self.current_equity) / self.peak_equity)


class AggressiveScalingScalper:
    def __init__(self, plan: ScalingPlan | None = None, symbol: str = "EURUSD") -> None:
        self.plan = plan or ScalingPlan()
        config = TradeConfig(
            symbol=symbol,
            risk_per_trade=min((plan or ScalingPlan()).max_risk_per_trade, 0.02),
            min_confluence=(plan or ScalingPlan()).min_confluence,
        )
        self.engine = TradingUltima(config=config)
        self.state = ScalingState(
            plan=self.plan,
            current_equity=self.plan.starting_equity,
            peak_equity=self.plan.starting_equity,
        )

    def scan_once(self) -> dict[str, Any]:
        self.engine.start()
        try:
            snapshot = self.engine.tick()
        finally:
            self.engine.stop()
        self._update_state(snapshot)
        snapshot["scaling_state"] = self.state
        snapshot["scaling_plan"] = self.plan
        snapshot["live_trading"] = self.engine.config.execution_mode == ExecutionMode.LIVE
        return snapshot

    def should_continue(self) -> tuple[bool, str]:
        if self.state.current_equity >= self.plan.target_equity:
            return False, "Target equity reached"
        if self.state.drawdown >= self.plan.max_daily_drawdown:
            return False, "Daily drawdown guard active"
        if self.state.blocked_reason:
            return False, self.state.blocked_reason
        return True, "Scaling plan active"

    def _update_state(self, snapshot: dict[str, Any]) -> None:
        status = snapshot.get("status")
        reason = snapshot.get("reason", "")
        if status == "executed":
            self.state.trades_taken += 1
        if status == "blocked":
            self.state.blocked_reason = str(reason)
        else:
            self.state.blocked_reason = ""
        equity = self.engine.gateway.account_equity()
        if equity > 0:
            self.state.current_equity = equity if self.engine.gateway.connected else self.state.current_equity
            self.state.peak_equity = max(self.state.peak_equity, self.state.current_equity)
        self.state.updated_at = datetime.now(timezone.utc)


def scalper_snapshot() -> dict[str, Any]:
    return AggressiveScalingScalper().scan_once()


if __name__ == "__main__":
    print(scalper_snapshot())
