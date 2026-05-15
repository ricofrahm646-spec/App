from dataclasses import dataclass


@dataclass(slots=True)
class MT5TerminalSnapshot:
    terminal_path: str
    data_path: str
    active_symbol: str | None
    active_timeframe: str | None
    open_charts: list[str]


@dataclass(slots=True)
class InstallPlan:
    target_directory: str
    file_type: str
    post_install_action: str


class MT5ConnectorService:
    """Abstraction point for a future MT5 bridge or host-side installer."""

    def describe_installation(self, file_type: str) -> InstallPlan:
        destinations = {
            "expert": ("MQL5/Experts/JARVIS", "Compile and attach to matching chart."),
            "indicator": ("MQL5/Indicators/JARVIS", "Compile and expose in the navigator."),
            "script": ("MQL5/Scripts/JARVIS", "Compile and keep ready for one-click execution."),
        }
        target_directory, action = destinations.get(
            file_type,
            ("MQL5/Files/JARVIS", "Place file in the shared JARVIS data directory."),
        )
        return InstallPlan(
            target_directory=target_directory,
            file_type=file_type,
            post_install_action=action,
        )

    def sample_snapshot(self) -> MT5TerminalSnapshot:
        return MT5TerminalSnapshot(
            terminal_path="",
            data_path="",
            active_symbol="EURUSD",
            active_timeframe="M15",
            open_charts=["EURUSD:M15", "XAUUSD:M5"],
        )
