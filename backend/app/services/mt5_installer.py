from dataclasses import dataclass
from pathlib import Path

from app.core.config import Settings


@dataclass(slots=True)
class Mt5ChartContext:
    symbol: str
    timeframe: str
    chart_id: str


class Mt5InstallerService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def build_install_plan(self, *, file_name: str) -> list[str]:
        target_root = Path(self.settings.mt5_path or "C:/Program Files/MetaTrader 5")
        return [
            f"Copy {file_name} to {target_root / 'MQL5' / 'Experts'}",
            f"Compile {file_name} into an EX5 artifact via MetaEditor",
            "Validate that the expert is visible in the MT5 navigator",
            "Attach the expert to the active chart matching the configured symbol and timeframe",
        ]

    def detect_chart_context(self) -> list[Mt5ChartContext]:
        # Runtime chart discovery depends on a live terminal bridge and is exposed as a future integration seam.
        return [
            Mt5ChartContext(symbol="EURUSD", timeframe="M15", chart_id="chart-1"),
            Mt5ChartContext(symbol="XAUUSD", timeframe="M5", chart_id="chart-2"),
        ]
