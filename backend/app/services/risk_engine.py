from dataclasses import dataclass

from app.core.config import Settings


@dataclass(slots=True)
class RiskAssessment:
    approved: bool
    position_size: float
    notes: list[str]


class RiskEngine:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def calculate_position_size(
        self,
        *,
        balance: float,
        stop_loss_pips: float,
        pip_value: float,
        risk_fraction: float | None = None,
    ) -> RiskAssessment:
        if stop_loss_pips <= 0 or pip_value <= 0:
            raise ValueError("Stop loss and pip value must be positive.")

        applied_risk = min(risk_fraction or self.settings.jarvis_max_single_trade_risk, self.settings.jarvis_max_single_trade_risk)
        risk_amount = balance * applied_risk
        size = risk_amount / (stop_loss_pips * pip_value)
        notes = [
            f"Applied risk fraction: {applied_risk:.2%}",
            "Only one concurrent trade is allowed by policy.",
            "Opposing hedged exposure is blocked by JARVIS execution safeguards.",
        ]
        return RiskAssessment(approved=size > 0, position_size=round(size, 2), notes=notes)

    def should_emergency_close(self, floating_loss_fraction: float) -> bool:
        return floating_loss_fraction >= self.settings.jarvis_max_floating_loss_close

    def validate_trade_window(self, active_positions: int, requested_direction: str, open_directions: set[str]) -> list[str]:
        issues: list[str] = []
        if active_positions >= 1:
            issues.append("JARVIS allows a maximum of one active trade at a time.")
        if requested_direction.lower() in {"buy", "sell"} and open_directions and requested_direction.lower() not in open_directions:
            issues.append("JARVIS blocks simultaneous Buy and Sell exposure.")
        return issues
