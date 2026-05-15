"""Demo mean reversion skeleton — not financial advice."""

from dataclasses import dataclass


@dataclass
class Params:
    lookback: int = 20


def generate_signal(_bars) -> str | None:
    return None
