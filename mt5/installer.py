from dataclasses import dataclass


@dataclass(slots=True)
class MT5InstallRequest:
    artifact_name: str
    artifact_type: str
    symbol: str | None = None
    timeframe: str | None = None


@dataclass(slots=True)
class MT5InstallInstruction:
    copy_to: str
    compile_after_copy: bool
    chart_action: str


def build_install_instruction(request: MT5InstallRequest) -> MT5InstallInstruction:
    target = {
        "expert": "MQL5/Experts/JARVIS",
        "indicator": "MQL5/Indicators/JARVIS",
    }.get(request.artifact_type, "MQL5/Files/JARVIS")

    chart_action = "No automatic chart attachment."
    if request.symbol and request.timeframe:
        chart_action = f"Attach {request.artifact_name} to {request.symbol} {request.timeframe}."

    return MT5InstallInstruction(
        copy_to=target,
        compile_after_copy=True,
        chart_action=chart_action,
    )
