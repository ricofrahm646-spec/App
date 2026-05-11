"""
TRADING-ULTIMA
---------------

MetaTrader 5 execution and Smart Money Concepts analysis engine.

The module is designed to be operational when MetaTrader5 is installed and
connected, while defaulting to dry-run execution. It intentionally does not
promise profits or bypass broker/news controls; all live execution requires an
explicit environment opt-in and strict risk checks.
"""

from __future__ import annotations

import logging
import math
import os
import statistics
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Iterable, Literal

try:
    import MetaTrader5 as mt5  # type: ignore
except Exception:  # pragma: no cover - optional platform dependency
    mt5 = None  # type: ignore

import pandas as pd


LOG = logging.getLogger("trader_ultimate")


Side = Literal["buy", "sell"]


class ExecutionMode(str, Enum):
    DRY_RUN = "dry_run"
    LIVE = "live"


@dataclass(frozen=True)
class TradeConfig:
    symbol: str = os.getenv("JARVIS_SYMBOL", "EURUSD")
    timeframe: Any = None
    bars: int = int(os.getenv("JARVIS_BARS", "500"))
    risk_per_trade: float = float(os.getenv("JARVIS_RISK_PER_TRADE", "0.01"))
    max_spread_points: float = float(os.getenv("JARVIS_MAX_SPREAD_POINTS", "25"))
    min_confluence: float = float(os.getenv("JARVIS_MIN_CONFLUENCE", "0.90"))
    atr_period: int = int(os.getenv("JARVIS_ATR_PERIOD", "14"))
    magic: int = int(os.getenv("JARVIS_MAGIC", "300300"))
    deviation: int = int(os.getenv("JARVIS_DEVIATION", "20"))
    trail_atr_multiplier: float = float(os.getenv("JARVIS_TRAIL_ATR_MULTIPLIER", "1.25"))
    execution_mode: ExecutionMode = field(
        default_factory=lambda: ExecutionMode.LIVE
        if os.getenv("JARVIS_LIVE_TRADING", "").lower() in {"1", "true", "yes"}
        else ExecutionMode.DRY_RUN
    )
    news_blackout_minutes: int = int(os.getenv("JARVIS_NEWS_BLACKOUT_MINUTES", "30"))


@dataclass(frozen=True)
class NewsEvent:
    currency: str
    title: str
    impact: Literal["low", "medium", "high"]
    starts_at: datetime


@dataclass(frozen=True)
class SMCSignal:
    symbol: str
    side: Side
    confluence: float
    entry: float
    stop_loss: float
    take_profit: float
    order_block_price: float | None
    fvg_midpoint: float | None
    liquidity_sweep_price: float | None
    reasons: tuple[str, ...]
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def risk_reward(self) -> float:
        risk = abs(self.entry - self.stop_loss)
        reward = abs(self.take_profit - self.entry)
        return reward / risk if risk else 0.0


class NewsProtector:
    """Simple high-impact news blackout gate with optional injected calendar."""

    def __init__(self, events: Iterable[NewsEvent] | None = None) -> None:
        self._events = list(events or [])

    def add_event(self, event: NewsEvent) -> None:
        self._events.append(event)

    def is_blocked(self, symbol: str, now: datetime, blackout_minutes: int) -> tuple[bool, str]:
        currencies = {symbol[:3].upper(), symbol[3:6].upper()} if len(symbol) >= 6 else {symbol.upper()}
        window = timedelta(minutes=blackout_minutes)
        for event in self._events:
            if event.impact != "high" or event.currency.upper() not in currencies:
                continue
            if abs(event.starts_at - now) <= window:
                return True, f"High-impact news blackout: {event.currency} {event.title}"
        return False, "No high-impact news blackout"


class MT5Gateway:
    """Small adapter around MetaTrader5 so the rest of the system is testable."""

    def __init__(self, config: TradeConfig) -> None:
        self.config = config
        self.connected = False

    def initialize(self) -> bool:
        if mt5 is None:
            LOG.warning("MetaTrader5 package unavailable; using dry-run data path")
            return False
        if self.config.timeframe is None:
            object.__setattr__(self.config, "timeframe", mt5.TIMEFRAME_M1)
        self.connected = bool(mt5.initialize())
        if not self.connected:
            LOG.error("MT5 initialize failed: %s", mt5.last_error())
        return self.connected

    def shutdown(self) -> None:
        if mt5 is not None and self.connected:
            mt5.shutdown()
        self.connected = False

    def rates(self) -> pd.DataFrame:
        if mt5 is None or not self.connected:
            return self._synthetic_rates()
        timeframe = self.config.timeframe or mt5.TIMEFRAME_M1
        raw = mt5.copy_rates_from_pos(self.config.symbol, timeframe, 0, self.config.bars)
        if raw is None:
            LOG.error("MT5 rates unavailable: %s", mt5.last_error())
            return pd.DataFrame()
        frame = pd.DataFrame(raw)
        frame["time"] = pd.to_datetime(frame["time"], unit="s", utc=True)
        return frame

    def spread_points(self) -> float:
        if mt5 is None or not self.connected:
            return 0.0
        tick = mt5.symbol_info_tick(self.config.symbol)
        info = mt5.symbol_info(self.config.symbol)
        if tick is None or info is None or not info.point:
            return math.inf
        return abs(tick.ask - tick.bid) / info.point

    def account_equity(self) -> float:
        if mt5 is None or not self.connected:
            return 1000.0
        account = mt5.account_info()
        return float(account.equity) if account else 0.0

    def send_order(self, signal: SMCSignal, volume: float) -> dict[str, Any]:
        if self.config.execution_mode != ExecutionMode.LIVE or mt5 is None or not self.connected:
            return {
                "mode": ExecutionMode.DRY_RUN.value,
                "accepted": True,
                "symbol": signal.symbol,
                "side": signal.side,
                "volume": volume,
                "entry": signal.entry,
                "sl": signal.stop_loss,
                "tp": signal.take_profit,
                "confluence": signal.confluence,
                "reasons": signal.reasons,
            }

        tick = mt5.symbol_info_tick(signal.symbol)
        if tick is None:
            return {"accepted": False, "reason": "No MT5 tick available"}
        order_type = mt5.ORDER_TYPE_BUY if signal.side == "buy" else mt5.ORDER_TYPE_SELL
        price = tick.ask if signal.side == "buy" else tick.bid
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": signal.symbol,
            "volume": volume,
            "type": order_type,
            "price": price,
            "sl": signal.stop_loss,
            "tp": signal.take_profit,
            "deviation": self.config.deviation,
            "magic": self.config.magic,
            "comment": "JARVIS V300 SMC",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        result = mt5.order_send(request)
        if result is None:
            return {"accepted": False, "reason": f"order_send failed: {mt5.last_error()}"}
        payload = result._asdict()
        payload["accepted"] = payload.get("retcode") == mt5.TRADE_RETCODE_DONE
        return payload

    def update_trailing_stops(self, atr: float) -> list[dict[str, Any]]:
        if mt5 is None or not self.connected:
            return []
        positions = mt5.positions_get(symbol=self.config.symbol) or []
        updates: list[dict[str, Any]] = []
        for position in positions:
            tick = mt5.symbol_info_tick(position.symbol)
            if tick is None:
                continue
            if position.type == mt5.POSITION_TYPE_BUY:
                proposed_sl = tick.bid - (atr * self.config.trail_atr_multiplier)
                should_move = proposed_sl > float(position.sl or 0)
            else:
                proposed_sl = tick.ask + (atr * self.config.trail_atr_multiplier)
                should_move = position.sl == 0 or proposed_sl < float(position.sl)
            if not should_move:
                continue
            request = {
                "action": mt5.TRADE_ACTION_SLTP,
                "position": position.ticket,
                "symbol": position.symbol,
                "sl": proposed_sl,
                "tp": position.tp,
                "magic": self.config.magic,
                "comment": "JARVIS trailing stop",
            }
            result = mt5.order_send(request)
            updates.append(result._asdict() if result else {"error": mt5.last_error()})
        return updates

    def _synthetic_rates(self) -> pd.DataFrame:
        now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
        rows: list[dict[str, Any]] = []
        price = 1.0800
        for index in range(self.config.bars):
            drift = math.sin(index / 11) * 0.00015
            impulse = 0.00035 if index % 97 == 0 else (-0.00030 if index % 83 == 0 else 0)
            open_price = price
            close = max(0.0001, open_price + drift + impulse)
            high = max(open_price, close) + 0.00025 + abs(math.sin(index)) * 0.00005
            low = min(open_price, close) - 0.00025 - abs(math.cos(index)) * 0.00005
            rows.append(
                {
                    "time": now - timedelta(minutes=self.config.bars - index),
                    "open": open_price,
                    "high": high,
                    "low": low,
                    "close": close,
                    "tick_volume": 100 + (index % 50),
                    "spread": 10,
                    "real_volume": 0,
                }
            )
            price = close
        return pd.DataFrame(rows)


class SMCAnalyzer:
    """Implements deterministic SMC feature extraction for M1 scalping signals."""

    def __init__(self, config: TradeConfig) -> None:
        self.config = config

    def analyze(self, rates: pd.DataFrame) -> SMCSignal | None:
        required = {"open", "high", "low", "close"}
        if rates.empty or not required.issubset(rates.columns) or len(rates) < 60:
            return None

        frame = rates.copy().reset_index(drop=True)
        atr = self.atr(frame).iloc[-1]
        if not atr or math.isnan(atr):
            return None

        order_block = self._latest_order_block(frame)
        fvg = self._latest_fvg(frame)
        sweep = self._latest_liquidity_sweep(frame)
        structure = self._market_structure(frame)
        momentum = self._momentum(frame)

        last_close = float(frame.iloc[-1]["close"])
        reasons: list[str] = []
        buy_score = 0.0
        sell_score = 0.0

        if order_block:
            side, price = order_block
            if side == "buy":
                buy_score += 0.24
                reasons.append(f"Bullish order block at {price:.5f}")
            else:
                sell_score += 0.24
                reasons.append(f"Bearish order block at {price:.5f}")

        if fvg:
            side, midpoint = fvg
            if side == "buy" and last_close >= midpoint:
                buy_score += 0.21
                reasons.append(f"Bullish FVG respected at {midpoint:.5f}")
            elif side == "sell" and last_close <= midpoint:
                sell_score += 0.21
                reasons.append(f"Bearish FVG respected at {midpoint:.5f}")

        if sweep:
            side, price = sweep
            if side == "buy":
                buy_score += 0.22
                reasons.append(f"Sell-side liquidity sweep at {price:.5f}")
            else:
                sell_score += 0.22
                reasons.append(f"Buy-side liquidity sweep at {price:.5f}")

        if structure == "bullish":
            buy_score += 0.18
            reasons.append("Bullish market structure shift")
        elif structure == "bearish":
            sell_score += 0.18
            reasons.append("Bearish market structure shift")

        if momentum > 0:
            buy_score += min(0.15, abs(momentum) * 120)
            reasons.append("Positive short-term momentum")
        elif momentum < 0:
            sell_score += min(0.15, abs(momentum) * 120)
            reasons.append("Negative short-term momentum")

        side: Side = "buy" if buy_score >= sell_score else "sell"
        raw_score = max(buy_score, sell_score)
        confluence = min(0.99, raw_score)
        if confluence < self.config.min_confluence:
            return None

        stop_distance = max(atr * 1.2, last_close * 0.0004)
        target_distance = stop_distance * 1.8
        if side == "buy":
            stop_loss = last_close - stop_distance
            take_profit = last_close + target_distance
        else:
            stop_loss = last_close + stop_distance
            take_profit = last_close - target_distance

        return SMCSignal(
            symbol=self.config.symbol,
            side=side,
            confluence=confluence,
            entry=last_close,
            stop_loss=stop_loss,
            take_profit=take_profit,
            order_block_price=order_block[1] if order_block else None,
            fvg_midpoint=fvg[1] if fvg else None,
            liquidity_sweep_price=sweep[1] if sweep else None,
            reasons=tuple(reasons),
        )

    def atr(self, frame: pd.DataFrame) -> pd.Series:
        high = frame["high"].astype(float)
        low = frame["low"].astype(float)
        close = frame["close"].astype(float)
        previous_close = close.shift(1)
        true_range = pd.concat(
            [(high - low), (high - previous_close).abs(), (low - previous_close).abs()],
            axis=1,
        ).max(axis=1)
        return true_range.rolling(self.config.atr_period).mean()

    def _latest_order_block(self, frame: pd.DataFrame) -> tuple[Side, float] | None:
        recent = frame.tail(40).reset_index(drop=True)
        bodies = (recent["close"] - recent["open"]).abs()
        median_body = float(statistics.median(bodies)) if len(bodies) else 0.0
        for index in range(len(recent) - 4, 2, -1):
            candle = recent.iloc[index]
            next_candle = recent.iloc[index + 1]
            body = abs(float(candle.close) - float(candle.open))
            impulse = abs(float(next_candle.close) - float(next_candle.open))
            if median_body and impulse < median_body * 1.4:
                continue
            if candle.close < candle.open and next_candle.close > next_candle.open:
                return "buy", float((candle.open + candle.close) / 2)
            if candle.close > candle.open and next_candle.close < next_candle.open:
                return "sell", float((candle.open + candle.close) / 2)
        return None

    def _latest_fvg(self, frame: pd.DataFrame) -> tuple[Side, float] | None:
        recent = frame.tail(60).reset_index(drop=True)
        for index in range(len(recent) - 1, 1, -1):
            first = recent.iloc[index - 2]
            third = recent.iloc[index]
            if float(first.high) < float(third.low):
                return "buy", float((first.high + third.low) / 2)
            if float(first.low) > float(third.high):
                return "sell", float((first.low + third.high) / 2)
        return None

    def _latest_liquidity_sweep(self, frame: pd.DataFrame) -> tuple[Side, float] | None:
        recent = frame.tail(50).reset_index(drop=True)
        last = recent.iloc[-1]
        prior = recent.iloc[:-1]
        prior_high = float(prior["high"].max())
        prior_low = float(prior["low"].min())
        if float(last.low) < prior_low and float(last.close) > prior_low:
            return "buy", float(last.low)
        if float(last.high) > prior_high and float(last.close) < prior_high:
            return "sell", float(last.high)
        return None

    def _market_structure(self, frame: pd.DataFrame) -> Literal["bullish", "bearish", "neutral"]:
        recent = frame.tail(30)
        highs = recent["high"].astype(float)
        lows = recent["low"].astype(float)
        if highs.iloc[-1] > highs.iloc[:15].max() and lows.iloc[-1] > lows.iloc[:15].min():
            return "bullish"
        if lows.iloc[-1] < lows.iloc[:15].min() and highs.iloc[-1] < highs.iloc[:15].max():
            return "bearish"
        return "neutral"

    def _momentum(self, frame: pd.DataFrame) -> float:
        close = frame["close"].astype(float)
        fast = close.tail(5).mean()
        slow = close.tail(20).mean()
        return float(fast - slow)


class RiskManager:
    def __init__(self, config: TradeConfig) -> None:
        self.config = config

    def volume_for(self, equity: float, signal: SMCSignal) -> float:
        risk_amount = equity * self.config.risk_per_trade
        stop_distance = abs(signal.entry - signal.stop_loss)
        if stop_distance <= 0:
            return 0.0
        raw_volume = risk_amount / (stop_distance * 100_000)
        return max(0.01, round(min(raw_volume, 10.0), 2))

    def validate(self, signal: SMCSignal, spread_points: float, news_blocked: bool) -> tuple[bool, list[str]]:
        errors: list[str] = []
        if signal.confluence < self.config.min_confluence:
            errors.append(f"Confluence {signal.confluence:.2%} below threshold")
        if signal.risk_reward < 1.2:
            errors.append(f"Risk/reward {signal.risk_reward:.2f} below minimum")
        if spread_points > self.config.max_spread_points:
            errors.append(f"Spread {spread_points:.1f} points above maximum")
        if news_blocked:
            errors.append("News protection active")
        return not errors, errors


class TradingUltima:
    def __init__(self, config: TradeConfig | None = None, news: NewsProtector | None = None) -> None:
        self.config = config or TradeConfig()
        self.gateway = MT5Gateway(self.config)
        self.analyzer = SMCAnalyzer(self.config)
        self.risk = RiskManager(self.config)
        self.news = news or NewsProtector()

    def start(self) -> bool:
        return self.gateway.initialize()

    def stop(self) -> None:
        self.gateway.shutdown()

    def tick(self) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        rates = self.gateway.rates()
        if rates.empty:
            return {"status": "idle", "reason": "No rates available", "time": now.isoformat()}

        atr = float(self.analyzer.atr(rates).iloc[-1])
        trailing_updates = self.gateway.update_trailing_stops(atr)
        signal = self.analyzer.analyze(rates)
        if signal is None:
            return {
                "status": "idle",
                "reason": "No 90%+ confluence signal",
                "trailing_updates": trailing_updates,
                "time": now.isoformat(),
            }

        news_blocked, news_reason = self.news.is_blocked(
            self.config.symbol, now, self.config.news_blackout_minutes
        )
        spread = self.gateway.spread_points()
        ok, errors = self.risk.validate(signal, spread, news_blocked)
        if not ok:
            return {
                "status": "blocked",
                "reason": "; ".join(errors),
                "news": news_reason,
                "signal": signal,
                "time": now.isoformat(),
            }

        equity = self.gateway.account_equity()
        volume = self.risk.volume_for(equity, signal)
        order = self.gateway.send_order(signal, volume)
        return {
            "status": "executed" if order.get("accepted") else "rejected",
            "signal": signal,
            "order": order,
            "spread_points": spread,
            "trailing_updates": trailing_updates,
            "time": now.isoformat(),
        }

    def run_forever(self, interval_seconds: float = 5.0) -> None:
        self.start()
        try:
            while True:
                LOG.info("Trading tick: %s", self.tick())
                time.sleep(interval_seconds)
        finally:
            self.stop()


def latest_snapshot() -> dict[str, Any]:
    engine = TradingUltima()
    engine.start()
    try:
        return engine.tick()
    finally:
        engine.stop()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    print(latest_snapshot())
