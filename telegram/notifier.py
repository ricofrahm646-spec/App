from dataclasses import dataclass


@dataclass(slots=True)
class TelegramMessage:
    title: str
    body: str
    severity: str = "info"


def build_trade_message(event: str, symbol: str, direction: str, detail: str) -> TelegramMessage:
    return TelegramMessage(
        title=f"JARVIS {event}",
        body=f"{symbol} {direction}\n{detail}",
        severity="warning" if event.lower() == "risk" else "info",
    )
