"""
Trade logger for the Hardcore Growth Mode trading bot.

Appends every closed trade to data/history.csv and prints a rolling
performance summary (total PnL, win-rate, best/worst trade).
"""

import csv
import logging
import os
from datetime import datetime, timezone
from typing import List

import config

_CSV_FIELDS = [
    "timestamp",
    "symbol",
    "score",
    "buy_price",
    "sell_price",
    "amount",
    "pnl_eur",
    "pnl_pct",
    "reason",
]


class TradeLogger:
    """Appends trade records to a CSV file and logs summary statistics."""

    def __init__(self) -> None:
        os.makedirs(config.DATA_DIR, exist_ok=True)
        self._ensure_header()

    def log_trade(self, record: dict) -> None:
        """Append one closed-trade record to history.csv."""
        row = {field: record.get(field, "") for field in _CSV_FIELDS}
        row["timestamp"] = datetime.now(tz=timezone.utc).isoformat()

        with open(config.HISTORY_FILE, "a", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=_CSV_FIELDS)
            writer.writerow(row)

        logging.info(
            "Logged trade: %s PnL=%.4f EUR (%.2f%%) [%s]",
            row["symbol"],
            float(row.get("pnl_eur") or 0),
            float(row.get("pnl_pct") or 0),
            row["reason"],
        )

    def log_trades(self, records: List[dict]) -> None:
        for record in records:
            self.log_trade(record)

    def print_summary(self) -> None:
        """Read history.csv and log a brief performance summary."""
        trades = self._read_all()
        if not trades:
            logging.info("No trades recorded yet.")
            return

        total_pnl = sum(t["pnl_eur"] for t in trades)
        wins = [t for t in trades if t["pnl_eur"] > 0]
        win_rate = len(wins) / len(trades) * 100
        best = max(trades, key=lambda t: t["pnl_pct"])
        worst = min(trades, key=lambda t: t["pnl_pct"])

        logging.info(
            "📊 Performance | trades=%d | total_PnL=%.4f EUR | win_rate=%.1f%% "
            "| best=%s(%.2f%%) | worst=%s(%.2f%%)",
            len(trades),
            total_pnl,
            win_rate,
            best["symbol"],
            best["pnl_pct"],
            worst["symbol"],
            worst["pnl_pct"],
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _ensure_header(self) -> None:
        if not os.path.exists(config.HISTORY_FILE):
            with open(config.HISTORY_FILE, "w", newline="", encoding="utf-8") as fh:
                writer = csv.DictWriter(fh, fieldnames=_CSV_FIELDS)
                writer.writeheader()

    def _read_all(self) -> list:
        if not os.path.exists(config.HISTORY_FILE):
            return []
        rows = []
        with open(config.HISTORY_FILE, newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                try:
                    rows.append(
                        {
                            "symbol": row["symbol"],
                            "pnl_eur": float(row.get("pnl_eur") or 0),
                            "pnl_pct": float(row.get("pnl_pct") or 0),
                        }
                    )
                except (ValueError, KeyError):
                    pass
        return rows
