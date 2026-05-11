from __future__ import annotations

import math
import os
import random
from collections import deque
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Deque, Iterable, Optional, Sequence

import numpy as np

try:
    import feedparser
except Exception:  # pragma: no cover - optional at runtime
    feedparser = None

try:
    import MetaTrader5 as mt5
except Exception:  # pragma: no cover - optional at runtime
    mt5 = None


UTC = timezone.utc


@dataclass(slots=True)
class Candle:
    time: datetime
    open: float
    high: float
    low: float
    close: float
    tick_volume: float = 0.0


@dataclass(slots=True)
class TradeSignal:
    symbol: str
    direction: str
    entry: float
    stop_loss: float
    take_profit: float
    confluence: float
    reasons: list[str]
    detected_at: datetime
    risk_reward: float
    metadata: dict[str, float | str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["detected_at"] = self.detected_at.isoformat()
        return payload


@dataclass(slots=True)
class ExecutionReport:
    mode: str
    accepted: bool
    message: str
    signal: Optional[TradeSignal] = None


@dataclass(slots=True)
class EngineSnapshot:
    timestamp: datetime
    symbol: str
    mode: str
    balance: float
    equity: float
    open_positions: int
    latest_signal: Optional[dict]
    recent_signals: list[dict]
    logs: list[str]
    recent_candles: list[dict]
    diagnostics: dict


class NewsProtection:
    """Blocks entries when fresh macro headlines hit the market."""

    FEEDS = (
        "https://feeds.reuters.com/reuters/businessNews",
        "https://feeds.reuters.com/reuters/worldNews",
        "https://www.ecb.europa.eu/rss/press.html",
    )

    KEYWORDS = {
        "EURUSD": ("eur", "usd", "ecb", "fed", "cpi", "inflation", "nfp", "payroll"),
        "GBPUSD": ("gbp", "usd", "boe", "fed", "cpi", "inflation", "nfp", "payroll"),
        "USDJPY": ("usd", "jpy", "boj", "fed", "cpi", "inflation", "nfp", "payroll"),
        "XAUUSD": ("gold", "usd", "fed", "yield", "inflation", "risk", "safe haven"),
    }

    def __init__(self, lookback_minutes: int = 45) -> None:
        self.lookback = timedelta(minutes=lookback_minutes)

    def _parse_feeds(self) -> list[dict]:
        if feedparser is None:
            return []

        entries: list[dict] = []
        for url in self.FEEDS:
            try:
                parsed = feedparser.parse(url)
            except Exception:
                continue
            for entry in getattr(parsed, "entries", []):
                published = None
                published_struct = entry.get("published_parsed")
                if published_struct:
                    published = datetime(*published_struct[:6], tzinfo=UTC)
                entries.append(
                    {
                        "title": entry.get("title", ""),
                        "summary": entry.get("summary", ""),
                        "link": entry.get("link", ""),
                        "published": published,
                    }
                )
        return entries

    def recent_macro_hits(self, symbol: str, now: Optional[datetime] = None) -> list[str]:
        now = now or datetime.now(UTC)
        hits: list[str] = []
        keywords = self.KEYWORDS.get(symbol.upper(), tuple())
        for entry in self._parse_feeds():
            published = entry["published"]
            if not published or now - published > self.lookback:
                continue
            blob = f'{entry["title"]} {entry["summary"]}'.lower()
            if any(keyword in blob for keyword in keywords):
                hits.append(entry["title"])
        return hits[:6]

    def is_blocked(self, symbol: str, now: Optional[datetime] = None) -> tuple[bool, list[str]]:
        hits = self.recent_macro_hits(symbol=symbol, now=now)
        return bool(hits), hits


class SyntheticMarket:
    """Fallback feed so the full system remains testable without MT5."""

    DEFAULT_PRICES = {
        "EURUSD": 1.0845,
        "GBPUSD": 1.2610,
        "USDJPY": 154.1000,
        "XAUUSD": 2320.0,
    }

    def __init__(self) -> None:
        self.seed = random.Random(7)
        self.last_price: dict[str, float] = {}

    def generate(self, symbol: str, count: int = 400) -> list[Candle]:
        price = self.last_price.get(symbol, self.DEFAULT_PRICES.get(symbol, 1.0))
        now = datetime.now(UTC).replace(second=0, microsecond=0)
        candles: list[Candle] = []
        drift = 0.00002 if symbol != "XAUUSD" else 0.08
        amplitude = 0.00035 if symbol != "XAUUSD" else 1.4

        for offset in range(count, 0, -1):
            ts = now - timedelta(minutes=offset - 1)
            open_price = price
            base_move = math.sin((count - offset) / 9.5) * amplitude * 0.35
            noise = self.seed.uniform(-amplitude, amplitude)
            close_price = max(0.0001, open_price + drift + base_move + noise * 0.35)
            wick_span = abs(noise) * 0.9 + amplitude * 0.25
            high = max(open_price, close_price) + wick_span
            low = min(open_price, close_price) - wick_span
            candles.append(
                Candle(
                    time=ts,
                    open=open_price,
                    high=high,
                    low=low,
                    close=close_price,
                    tick_volume=150 + abs(noise) * 1000,
                )
            )
            price = close_price
        self.last_price[symbol] = price
        return candles


class MetaTraderConnector:
    def __init__(self, mode: str = "paper", balance: float = 1000.0) -> None:
        self.mode = mode
        self.initialized = False
        self.synthetic = SyntheticMarket()
        self.paper_balance = balance
        self.paper_equity = balance
        self.paper_positions: list[dict] = []

    def initialize(self) -> bool:
        if self.initialized:
            return True
        if self.mode != "live" or mt5 is None:
            self.initialized = True
            return True
        self.initialized = bool(mt5.initialize())
        return self.initialized

    def fetch_candles(self, symbol: str, count: int = 400) -> list[Candle]:
        self.initialize()
        if self.mode == "live" and mt5 is not None and self.initialized:
            rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 0, count)
            if rates is not None and len(rates) > 0:
                return [
                    Candle(
                        time=datetime.fromtimestamp(int(row["time"]), tz=UTC),
                        open=float(row["open"]),
                        high=float(row["high"]),
                        low=float(row["low"]),
                        close=float(row["close"]),
                        tick_volume=float(row["tick_volume"]),
                    )
                    for row in rates
                ]
        return self.synthetic.generate(symbol=symbol, count=count)

    def account_snapshot(self) -> dict[str, float]:
        self.initialize()
        if self.mode == "live" and mt5 is not None and self.initialized:
            info = mt5.account_info()
            if info:
                return {"balance": float(info.balance), "equity": float(info.equity)}
        return {"balance": self.paper_balance, "equity": self.paper_equity}

    def _paper_profit(self, position: dict, last_price: float) -> float:
        direction = 1 if position["direction"] == "buy" else -1
        return direction * (last_price - position["entry"]) * 100000 * position["volume"]

    def update_open_positions(self, last_price: float, atr: float) -> list[str]:
        events: list[str] = []
        surviving: list[dict] = []
        for position in self.paper_positions:
            direction = position["direction"]
            hit_stop = last_price <= position["stop_loss"] if direction == "buy" else last_price >= position["stop_loss"]
            hit_target = last_price >= position["take_profit"] if direction == "buy" else last_price <= position["take_profit"]
            profit = self._paper_profit(position, last_price)

            if profit > atr * 100000 * position["volume"] * 0.7:
                if direction == "buy":
                    position["stop_loss"] = max(position["stop_loss"], last_price - atr * 0.6)
                else:
                    position["stop_loss"] = min(position["stop_loss"], last_price + atr * 0.6)

            if hit_stop or hit_target:
                self.paper_balance += profit
                events.append(
                    f'{position["direction"].upper()} closed at {last_price:.5f} ({profit:+.2f} EUR paper P/L)'
                )
                continue
            surviving.append(position)
        self.paper_positions = surviving
        self.paper_equity = self.paper_balance + sum(self._paper_profit(pos, last_price) for pos in self.paper_positions)
        return events

    def submit_order(self, signal: TradeSignal, volume: float = 0.1) -> ExecutionReport:
        self.initialize()
        if self.mode == "live" and mt5 is not None and self.initialized:
            tick = mt5.symbol_info_tick(signal.symbol)
            if tick is None:
                return ExecutionReport(mode=self.mode, accepted=False, message="MT5 tick data unavailable", signal=signal)
            order_type = mt5.ORDER_TYPE_BUY if signal.direction == "buy" else mt5.ORDER_TYPE_SELL
            price = tick.ask if signal.direction == "buy" else tick.bid
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": signal.symbol,
                "volume": volume,
                "type": order_type,
                "price": price,
                "sl": signal.stop_loss,
                "tp": signal.take_profit,
                "deviation": 15,
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
                "comment": f"JARVIS:{signal.confluence:.2f}",
            }
            result = mt5.order_send(request)
            accepted = bool(result and result.retcode == mt5.TRADE_RETCODE_DONE)
            message = f"MT5 order {'accepted' if accepted else 'rejected'}"
            return ExecutionReport(mode=self.mode, accepted=accepted, message=message, signal=signal)

        self.paper_positions.append(
            {
                "symbol": signal.symbol,
                "direction": signal.direction,
                "entry": signal.entry,
                "stop_loss": signal.stop_loss,
                "take_profit": signal.take_profit,
                "volume": volume,
                "opened_at": datetime.now(UTC),
            }
        )
        return ExecutionReport(
            mode=self.mode,
            accepted=True,
            message=f"Paper order opened: {signal.direction.upper()} {signal.symbol} @ {signal.entry:.5f}",
            signal=signal,
        )


class SMCAnalyzer:
    def __init__(self, min_confluence: float = 0.9) -> None:
        self.min_confluence = min_confluence

    @staticmethod
    def _ranges(candles: Sequence[Candle]) -> list[float]:
        return [candle.high - candle.low for candle in candles]

    @staticmethod
    def ema(values: Sequence[float], period: int) -> list[float]:
        if not values:
            return []
        alpha = 2 / (period + 1)
        result = [values[0]]
        for value in values[1:]:
            result.append(alpha * value + (1 - alpha) * result[-1])
        return result

    def average_true_range(self, candles: Sequence[Candle], period: int = 14) -> float:
        if len(candles) < 2:
            return 0.0
        tr_values = []
        for previous, current in zip(candles[:-1], candles[1:]):
            tr = max(
                current.high - current.low,
                abs(current.high - previous.close),
                abs(current.low - previous.close),
            )
            tr_values.append(tr)
        window = tr_values[-period:] if len(tr_values) >= period else tr_values
        return float(np.mean(window)) if window else 0.0

    def detect_swings(self, candles: Sequence[Candle], width: int = 3) -> dict[str, list[int]]:
        swing_highs: list[int] = []
        swing_lows: list[int] = []
        for index in range(width, len(candles) - width):
            window = candles[index - width : index + width + 1]
            current = candles[index]
            if current.high == max(item.high for item in window):
                swing_highs.append(index)
            if current.low == min(item.low for item in window):
                swing_lows.append(index)
        return {"highs": swing_highs, "lows": swing_lows}

    def detect_liquidity_sweeps(self, candles: Sequence[Candle], swings: dict[str, list[int]]) -> list[dict]:
        sweeps: list[dict] = []
        for idx in swings["highs"][-8:]:
            level = candles[idx].high
            for probe in range(idx + 1, min(len(candles), idx + 9)):
                candle = candles[probe]
                if candle.high > level and candle.close < level:
                    sweeps.append({"direction": "sell", "index": probe, "level": level})
                    break
        for idx in swings["lows"][-8:]:
            level = candles[idx].low
            for probe in range(idx + 1, min(len(candles), idx + 9)):
                candle = candles[probe]
                if candle.low < level and candle.close > level:
                    sweeps.append({"direction": "buy", "index": probe, "level": level})
                    break
        return sweeps

    def detect_fair_value_gaps(self, candles: Sequence[Candle]) -> list[dict]:
        gaps: list[dict] = []
        avg_range = float(np.mean(self._ranges(candles[-50:]))) if candles else 0.0
        for index in range(2, len(candles)):
            left, mid, right = candles[index - 2], candles[index - 1], candles[index]
            impulse = abs(mid.close - mid.open) > avg_range * 0.6
            if left.high < right.low and impulse:
                gaps.append(
                    {"direction": "buy", "index": index, "lower": left.high, "upper": right.low}
                )
            if left.low > right.high and impulse:
                gaps.append(
                    {"direction": "sell", "index": index, "lower": right.high, "upper": left.low}
                )
        return gaps

    def detect_orderblocks(self, candles: Sequence[Candle]) -> list[dict]:
        orderblocks: list[dict] = []
        avg_range = float(np.mean(self._ranges(candles[-50:]))) if candles else 0.0
        for index in range(1, len(candles) - 2):
            current = candles[index]
            nxt = candles[index + 1]
            displacement = abs(nxt.close - nxt.open) > avg_range * 1.2
            if displacement and current.close < current.open and nxt.close > current.high:
                orderblocks.append(
                    {
                        "direction": "buy",
                        "index": index,
                        "lower": current.low,
                        "upper": max(current.open, current.close),
                    }
                )
            if displacement and current.close > current.open and nxt.close < current.low:
                orderblocks.append(
                    {
                        "direction": "sell",
                        "index": index,
                        "lower": min(current.open, current.close),
                        "upper": current.high,
                    }
                )
        return orderblocks

    @staticmethod
    def session_multiplier(now: datetime) -> tuple[float, str]:
        hour = now.hour
        if 7 <= hour <= 10 or 13 <= hour <= 16:
            return 1.0, "London/New York active"
        if 5 <= hour <= 18:
            return 0.7, "Minor session activity"
        return 0.2, "Low-liquidity session"

    def build_signal(
        self,
        symbol: str,
        candles: Sequence[Candle],
        news_blocked: bool,
        news_hits: Sequence[str],
    ) -> tuple[Optional[TradeSignal], dict]:
        if len(candles) < 60:
            return None, {"error": "Not enough candles"}

        closes = [candle.close for candle in candles]
        ema_fast = self.ema(closes, 20)
        ema_slow = self.ema(closes, 50)
        atr = self.average_true_range(candles)
        swings = self.detect_swings(candles)
        sweeps = self.detect_liquidity_sweeps(candles, swings)
        fvgs = self.detect_fair_value_gaps(candles)
        orderblocks = self.detect_orderblocks(candles)
        latest = candles[-1]

        bullish_bias = ema_fast[-1] > ema_slow[-1] and latest.close > ema_fast[-1]
        bearish_bias = ema_fast[-1] < ema_slow[-1] and latest.close < ema_fast[-1]
        if not bullish_bias and not bearish_bias:
            return None, {"atr": atr, "reason": "No directional bias"}

        direction = "buy" if bullish_bias else "sell"
        same_sweeps = [item for item in sweeps if item["direction"] == direction and item["index"] >= len(candles) - 10]
        same_fvgs = [item for item in fvgs if item["direction"] == direction and item["index"] >= len(candles) - 20]
        same_orderblocks = [
            item for item in orderblocks if item["direction"] == direction and item["index"] >= len(candles) - 20
        ]

        reasons: list[str] = []
        score = 0.0

        score += 0.25
        reasons.append(f"EMA bias confirms {direction.upper()}")

        if same_sweeps:
            score += 0.20
            reasons.append("Liquidity sweep reclaimed")
        if same_fvgs:
            score += 0.20
            reasons.append("Fresh FVG aligned")
        if same_orderblocks:
            score += 0.15
            reasons.append("Orderblock in play")

        session_score, session_label = self.session_multiplier(latest.time)
        score += 0.10 * session_score
        reasons.append(session_label)

        if not news_blocked:
            score += 0.10
            reasons.append("News filter clear")
        elif news_hits:
            reasons.append("News block active")

        confluence = round(min(score, 0.99), 2)
        if confluence < self.min_confluence:
            return None, {
                "atr": atr,
                "direction": direction,
                "confluence": confluence,
                "reasons": reasons,
                "news_hits": list(news_hits),
            }

        if direction == "buy":
            stop_anchor = min(
                [latest.low - atr * 0.2]
                + [item["lower"] for item in same_orderblocks[-1:]]
                + [item["level"] for item in same_sweeps[-1:]]
            )
            stop_loss = stop_anchor
            take_profit = latest.close + (latest.close - stop_loss) * 2.0
        else:
            stop_anchor = max(
                [latest.high + atr * 0.2]
                + [item["upper"] for item in same_orderblocks[-1:]]
                + [item["level"] for item in same_sweeps[-1:]]
            )
            stop_loss = stop_anchor
            take_profit = latest.close - (stop_loss - latest.close) * 2.0

        risk = abs(latest.close - stop_loss)
        reward = abs(take_profit - latest.close)
        signal = TradeSignal(
            symbol=symbol,
            direction=direction,
            entry=latest.close,
            stop_loss=stop_loss,
            take_profit=take_profit,
            confluence=confluence,
            reasons=reasons,
            detected_at=latest.time,
            risk_reward=round(reward / risk, 2) if risk else 0.0,
            metadata={"atr": round(atr, 6), "session_score": session_score},
        )
        return signal, {
            "atr": atr,
            "direction": direction,
            "confluence": confluence,
            "reasons": reasons,
            "news_hits": list(news_hits),
        }


class TraderUltimate:
    def __init__(
        self,
        symbol: str = "EURUSD",
        mode: str | None = None,
        min_confluence: float = 0.9,
        start_balance: float = 1000.0,
    ) -> None:
        self.symbol = symbol
        self.mode = mode or os.getenv("TRADING_MODE", "paper")
        self.connector = MetaTraderConnector(mode=self.mode, balance=start_balance)
        self.news_guard = NewsProtection()
        self.analyzer = SMCAnalyzer(min_confluence=min_confluence)
        self.logs: Deque[str] = deque(maxlen=250)
        self.signal_history: Deque[TradeSignal] = deque(maxlen=40)
        self.equity_history: Deque[dict] = deque(maxlen=300)
        self.latest_candles: list[Candle] = []
        self.last_diagnostics: dict = {}
        self.log(
            "TraderUltimate online in "
            f"{self.mode.upper()} mode. Live execution requires a local MT5 session and explicit operator approval."
        )

    def log(self, message: str) -> None:
        timestamp = datetime.now(UTC).strftime("%H:%M:%S")
        self.logs.appendleft(f"[{timestamp}] {message}")

    def _record_equity(self, timestamp: datetime) -> None:
        snapshot = self.connector.account_snapshot()
        self.equity_history.append(
            {
                "time": timestamp.isoformat(),
                "balance": snapshot["balance"],
                "equity": snapshot["equity"],
            }
        )

    def run_cycle(self) -> EngineSnapshot:
        candles = self.connector.fetch_candles(symbol=self.symbol, count=400)
        self.latest_candles = candles
        latest = candles[-1]
        atr = self.analyzer.average_true_range(candles)
        for event in self.connector.update_open_positions(last_price=latest.close, atr=max(atr, 0.0001)):
            self.log(event)

        blocked, hits = self.news_guard.is_blocked(self.symbol, now=latest.time)
        signal, diagnostics = self.analyzer.build_signal(
            symbol=self.symbol,
            candles=candles,
            news_blocked=blocked,
            news_hits=hits,
        )
        self.last_diagnostics = diagnostics

        if signal:
            self.signal_history.appendleft(signal)
            if len(self.connector.paper_positions) < 2:
                report = self.connector.submit_order(signal)
                self.log(report.message)
            else:
                self.log("Signal detected but skipped: position cap reached")
        elif diagnostics.get("confluence") is not None:
            self.log(
                f"Scan complete: confluence {diagnostics['confluence']:.2f}, "
                f"below threshold {self.analyzer.min_confluence:.2f}"
            )
        else:
            self.log(f"Scan idle: {diagnostics.get('reason', 'market unavailable')}")

        self._record_equity(latest.time)
        return self.snapshot()

    def snapshot(self) -> EngineSnapshot:
        account = self.connector.account_snapshot()
        latest_signal = self.signal_history[0].to_dict() if self.signal_history else None
        candles = [
            {
                "time": candle.time.isoformat(),
                "open": candle.open,
                "high": candle.high,
                "low": candle.low,
                "close": candle.close,
            }
            for candle in self.latest_candles[-120:]
        ]
        return EngineSnapshot(
            timestamp=datetime.now(UTC),
            symbol=self.symbol,
            mode=self.mode,
            balance=account["balance"],
            equity=account["equity"],
            open_positions=len(self.connector.paper_positions),
            latest_signal=latest_signal,
            recent_signals=[signal.to_dict() for signal in list(self.signal_history)[:8]],
            logs=list(self.logs),
            recent_candles=candles,
            diagnostics=self.last_diagnostics,
        )

    def equity_curve(self) -> list[dict]:
        return list(self.equity_history)

    def status_payload(self) -> dict:
        snapshot = self.snapshot()
        return {
            "symbol": snapshot.symbol,
            "mode": snapshot.mode,
            "balance": snapshot.balance,
            "equity": snapshot.equity,
            "open_positions": snapshot.open_positions,
            "latest_signal": snapshot.latest_signal,
            "diagnostics": snapshot.diagnostics,
        }


def run_demo_cycles(cycles: int = 5, symbol: str = "EURUSD") -> list[dict]:
    trader = TraderUltimate(symbol=symbol, mode="paper")
    for _ in range(cycles):
        trader.run_cycle()
    return trader.equity_curve()


if __name__ == "__main__":
    trader = TraderUltimate()
    snapshot = trader.run_cycle()
    print(snapshot)
