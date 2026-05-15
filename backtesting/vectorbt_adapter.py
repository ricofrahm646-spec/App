from typing import Any

import pandas as pd


class VectorBTAdapter:
    def build_price_frame(self, candles: list[dict[str, Any]]) -> pd.DataFrame:
        frame = pd.DataFrame(candles)
        required = {"open", "high", "low", "close"}
        missing = required.difference(frame.columns)
        if missing:
            raise ValueError(f"Missing candle columns: {', '.join(sorted(missing))}")
        return frame
