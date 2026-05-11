"""JARVIS Trading-Ultima.

This module implements a MetaTrader 5 compatible M1 scalping engine with
Smart Money Concepts (SMC) style signal extraction. It is intentionally
paper-trading by default. Live order placement requires both configuration and
an explicit environment acknowledgement because leveraged trading can lose
money quickly and no software can guarantee a target return.
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import os
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Iterable, Sequence

try:
    import MetaTrader5 as mt5
except Exception:  # pragma: no cover - optional dependency on non-Windows CI
    mt5 = None  # type: ignore[assignment]

import numpy as np
import pandas as pd


LOGGER = logging.getLogger("jarvis.trader")
DEFAULT_LOG = Path("logs/trader_ultimate.jsonl")


class Side(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


@dataclass(frozen=True)
class TradingConfig:
    symbol: str = "EURUSD"
    timeframe_name: str = "M1"
    bars: int = 500
    paper_trading: bool = True
    confluence_threshold: float = 0.90
    risk_per_trade: float = 0.01
    max_spread_points: float = 30.0
    max_open_positions: int = 1
    atr_period: int = 14
    swing_lookback: int = 3
    news_blackout_minutes: int = 20
    trail_atr_multiple: float = 1.4
    min_rr: float = 1.5
    deviation: int = 10
    magic: int = 300_202_605
    log_path: Path = DEFAULT_LOG
    news_file: Path = Path("news_events.json")

    @classmethod
    def from_env(cls) -> "TradingConfig":
        return cls(
            symbol=os.getenv("JARVIS_SYMBOL", cls.symbol),
            paper_trading=os.getenv("JARVIS_PAPER_TRADING", "1") != "0",
            confluence_threshold=float(os.getenv("JARVIS_CONFLUENCE", "0.90")),
            risk_per_trade=float(os.getenv("JARVIS_RISK_PER_TRADE", "0.01")),
            max_spread_points=float(os.getenv("JARVIS_MAX_SPREAD", "30")),
            max_open_positions=int(os.getenv("JARVIS_MAX_POSITIONS", "1")),
        )


@dataclass(frozen=True)
class OrderBlock:
    side: Side
    start_time: datetime
    end_time: datetime
    high: float
    low: float
    impulse_ratio: float


@dataclass(frozen=True)
class FairValueGap:
    side: Side
    time: datetime
    upper: float
    lower: float
    size: float


@dataclass(frozen=True)
class LiquiditySweep:
    side: Side
    time: datetime
    swept_level: float
    rejection_close: float
    wick_ratio: float


@dataclass(frozen=True)
class TradeSignal:
    side: Side
    symbol: str
    confidence: float
    entry: float | None
    stop_loss: float | None
    take_profit: float | None
    reasons: tuple[str, ...]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_json(self) -> str:
        payload = asdict(self)
        payload["side"] = self.side.value
        payload["timestamp"] = self.timestamp.isoformat()
        return json.dumps(payload, sort_keys=True)


@dataclass(frozen=True)
class PaperPosition:
    ticket: str
    signal: TradeSignal
    opened_at: datetime
    volume: float


def setup_logging(level: int = logging.INFO) -> None:
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )


def timeframe_value(name: str) -> int:
    if mt5 is None:
        return 1
    mapping = {
        "M1": mt5.TIMEFRAME_M1,
        "M5": mt5.TIMEFRAME_M5,
        "M15": mt5.TIMEFRAME_M15,
        "H1": mt5.TIMEFRAME_H1,
    }
    return mapping.get(name.upper(), mt5.TIMEFRAME_M1)


def ensure_utc(value: Any) -> datetime:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    return datetime.fromtimestamp(float(value), tz=timezone.utc)


def normalise_rates(rates: Sequence[Any]) -> pd.DataFrame:
    df = pd.DataFrame(rates)
    if df.empty:
        return df
    if "time" in df:
        df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)
    for column in ("open", "high", "low", "close", "tick_volume", "spread"):
        if column in df:
            df[column] = pd.to_numeric(df[column], errors="coerce")
    return df.dropna(subset=["open", "high", "low", "close"]).reset_index(drop=True)


def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high_low = df["high"] - df["low"]
    high_close = (df["high"] - df["close"].shift()).abs()
    low_close = (df["low"] - df["close"].shift()).abs()
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return true_range.ewm(alpha=1 / period, adjust=False).mean()


def rsi(df: pd.DataFrame, period: int = 14) -> pd.Series:
    delta = df["close"].diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / period, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / period, adjust=False).mean()
    relative_strength = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + relative_strength))


class NewsProtection:
    """Simple local high-impact-news blackout checker.

    Expected optional JSON format:
    [
      {"time": "2026-05-11T14:30:00Z", "impact": "high", "symbols": ["EURUSD"]}
    ]
    """

    def __init__(self, events_file: Path, blackout_minutes: int) -> None:
        self.events_file = events_file
        self.blackout = timedelta(minutes=blackout_minutes)
        self._events = self._load_events()

    def _load_events(self) -> list[dict[str, Any]]:
        if not self.events_file.exists():
            return []
        try:
            payload = json.loads(self.events_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            LOGGER.warning("Could not load news events from %s: %s", self.events_file, exc)
            return []
        return payload if isinstance(payload, list) else []

    def blocked(self, symbol: str, now: datetime | None = None) -> tuple[bool, str | None]:
        now = now or datetime.now(timezone.utc)
        for event in self._events:
            if str(event.get("impact", "")).lower() not in {"high", "red", "critical"}:
                continue
            symbols = [str(item).upper() for item in event.get("symbols", [])]
            if symbols and symbol.upper() not in symbols and symbol[:3].upper() not in symbols:
                continue
            try:
                event_time = datetime.fromisoformat(str(event["time"]).replace("Z", "+00:00"))
            except (KeyError, ValueError):
                continue
            if abs(now - event_time.astimezone(timezone.utc)) <= self.blackout:
                return True, f"news blackout around {event_time.isoformat()}"
        return False, None


class SMCAnalyzer:
    """Extracts practical SMC signals from OHLC bars.

    The implementation uses deterministic price-action rules: displacement for
    order blocks, three-candle gaps for FVGs, and sweep-and-close-back behavior
    for liquidity sweeps.
    """

    def __init__(self, config: TradingConfig) -> None:
        self.config = config

    def prepare(self, df: pd.DataFrame) -> pd.DataFrame:
        prepared = df.copy()
        prepared["atr"] = atr(prepared, self.config.atr_period)
        prepared["rsi"] = rsi(prepared)
        prepared["body"] = (prepared["close"] - prepared["open"]).abs()
        prepared["range"] = (prepared["high"] - prepared["low"]).replace(0, np.nan)
        prepared["body_ratio"] = prepared["body"] / prepared["range"]
        return prepared

    def detect_order_blocks(self, df: pd.DataFrame) -> list[OrderBlock]:
        if len(df) < 30:
            return []
        prepared = self.prepare(df)
        blocks: list[OrderBlock] = []
        for idx in range(3, len(prepared) - 1):
            current = prepared.iloc[idx]
            previous = prepared.iloc[idx - 1]
            local_atr = float(current.get("atr", 0) or 0)
            if not math.isfinite(local_atr) or local_atr <= 0:
                continue
            displacement = abs(float(current["close"] - current["open"]))
            if displacement < 1.2 * local_atr or float(current.get("body_ratio", 0)) < 0.55:
                continue
            current_bullish = current["close"] > current["open"]
            previous_bearish = previous["close"] < previous["open"]
            previous_bullish = previous["close"] > previous["open"]
            if current_bullish and previous_bearish:
                blocks.append(
                    OrderBlock(
                        side=Side.BUY,
                        start_time=ensure_utc(previous["time"].to_pydatetime()),
                        end_time=ensure_utc(current["time"].to_pydatetime()),
                        high=float(previous["high"]),
                        low=float(previous["low"]),
                        impulse_ratio=displacement / local_atr,
                    )
                )
            elif not current_bullish and previous_bullish:
                blocks.append(
                    OrderBlock(
                        side=Side.SELL,
                        start_time=ensure_utc(previous["time"].to_pydatetime()),
                        end_time=ensure_utc(current["time"].to_pydatetime()),
                        high=float(previous["high"]),
                        low=float(previous["low"]),
                        impulse_ratio=displacement / local_atr,
                    )
                )
        return blocks[-20:]

    def detect_fvgs(self, df: pd.DataFrame) -> list[FairValueGap]:
        gaps: list[FairValueGap] = []
        if len(df) < 3:
            return gaps
        for idx in range(2, len(df)):
            first = df.iloc[idx - 2]
            third = df.iloc[idx]
            if float(first["high"]) < float(third["low"]):
                gaps.append(
                    FairValueGap(
                        side=Side.BUY,
                        time=ensure_utc(third["time"].to_pydatetime()),
                        lower=float(first["high"]),
                        upper=float(third["low"]),
                        size=float(third["low"] - first["high"]),
                    )
                )
            elif float(first["low"]) > float(third["high"]):
                gaps.append(
                    FairValueGap(
                        side=Side.SELL,
                        time=ensure_utc(third["time"].to_pydatetime()),
                        lower=float(third["high"]),
                        upper=float(first["low"]),
                        size=float(first["low"] - third["high"]),
                    )
                )
        return gaps[-30:]

    def detect_liquidity_sweeps(self, df: pd.DataFrame) -> list[LiquiditySweep]:
        sweeps: list[LiquiditySweep] = []
        lookback = max(5, self.config.swing_lookback * 3)
        if len(df) <= lookback:
            return sweeps
        for idx in range(lookback, len(df)):
            current = df.iloc[idx]
            window = df.iloc[idx - lookback : idx]
            prior_high = float(window["high"].max())
            prior_low = float(window["low"].min())
            candle_range = max(float(current["high"] - current["low"]), 1e-12)
            upper_wick = float(current["high"] - max(current["open"], current["close"]))
            lower_wick = float(min(current["open"], current["close"]) - current["low"])
            if float(current["high"]) > prior_high and float(current["close"]) < prior_high:
                sweeps.append(
                    LiquiditySweep(
                        side=Side.SELL,
                        time=ensure_utc(current["time"].to_pydatetime()),
                        swept_level=prior_high,
                        rejection_close=float(current["close"]),
                        wick_ratio=upper_wick / candle_range,
                    )
                )
            if float(current["low"]) < prior_low and float(current["close"]) > prior_low:
                sweeps.append(
                    LiquiditySweep(
                        side=Side.BUY,
                        time=ensure_utc(current["time"].to_pydatetime()),
                        swept_level=prior_low,
                        rejection_close=float(current["close"]),
                        wick_ratio=lower_wick / candle_range,
                    )
                )
        return sweeps[-20:]

    def market_bias(self, df: pd.DataFrame) -> tuple[Side, str]:
        if len(df) < 60:
            return Side.HOLD, "insufficient structure"
        ema_fast = df["close"].ewm(span=20, adjust=False).mean().iloc[-1]
        ema_slow = df["close"].ewm(span=50, adjust=False).mean().iloc[-1]
        last_close = float(df["close"].iloc[-1])
        if ema_fast > ema_slow and last_close > ema_fast:
            return Side.BUY, "20 EMA above 50 EMA with price above fast EMA"
        if ema_fast < ema_slow and last_close < ema_fast:
            return Side.SELL, "20 EMA below 50 EMA with price below fast EMA"
        return Side.HOLD, "mixed EMA structure"

    def build_signal(
        self,
        df: pd.DataFrame,
        symbol: str,
        spread_points: float | None = None,
        news_reason: str | None = None,
    ) -> TradeSignal:
        if df.empty or len(df) < 80:
            return TradeSignal(Side.HOLD, symbol, 0.0, None, None, None, ("insufficient bars",))

        prepared = self.prepare(df)
        order_blocks = self.detect_order_blocks(prepared)
        fvgs = self.detect_fvgs(prepared)
        sweeps = self.detect_liquidity_sweeps(prepared)
        bias, bias_reason = self.market_bias(prepared)
        last = prepared.iloc[-1]
        last_close = float(last["close"])
        local_atr = float(last.get("atr", 0) or 0)

        if news_reason:
            return TradeSignal(Side.HOLD, symbol, 0.0, None, None, None, (news_reason,))
        if spread_points is not None and spread_points > self.config.max_spread_points:
            return TradeSignal(
                Side.HOLD,
                symbol,
                0.0,
                None,
                None,
                None,
                (f"spread {spread_points:.1f} exceeds max {self.config.max_spread_points:.1f}",),
            )
        if bias is Side.HOLD or local_atr <= 0:
            return TradeSignal(Side.HOLD, symbol, 0.0, None, None, None, (bias_reason,))

        reasons: list[str] = [bias_reason]
        score = 0.20

        recent_sweep = self._latest_matching(sweeps, bias)
        if recent_sweep:
            score += 0.25 * min(1.0, max(0.0, recent_sweep.wick_ratio * 2))
            reasons.append(f"{bias.value} liquidity sweep at {recent_sweep.swept_level:.5f}")

        recent_fvg = self._latest_matching(fvgs, bias)
        if recent_fvg and recent_fvg.lower <= last_close <= recent_fvg.upper:
            score += 0.20
            reasons.append(f"price inside {bias.value} FVG {recent_fvg.lower:.5f}-{recent_fvg.upper:.5f}")
        elif recent_fvg and abs(last_close - (recent_fvg.lower + recent_fvg.upper) / 2) <= local_atr:
            score += 0.10
            reasons.append("price near matching FVG")

        recent_ob = self._latest_matching(order_blocks, bias)
        if recent_ob and recent_ob.low <= last_close <= recent_ob.high:
            score += 0.20
            reasons.append(f"price returned to {bias.value} order block")
        elif recent_ob and min(abs(last_close - recent_ob.low), abs(last_close - recent_ob.high)) <= local_atr:
            score += 0.10
            reasons.append("price near matching order block")

        last_rsi = float(last.get("rsi", 50) or 50)
        if bias is Side.BUY and 45 <= last_rsi <= 70:
            score += 0.10
            reasons.append(f"RSI supports long continuation ({last_rsi:.1f})")
        elif bias is Side.SELL and 30 <= last_rsi <= 55:
            score += 0.10
            reasons.append(f"RSI supports short continuation ({last_rsi:.1f})")

        volume_window = prepared["tick_volume"].tail(30)
        if not volume_window.empty and float(last["tick_volume"]) >= float(volume_window.quantile(0.65)):
            score += 0.05
            reasons.append("tick volume above local median")

        confidence = min(1.0, score)
        if confidence < self.config.confluence_threshold:
            return TradeSignal(bias, symbol, confidence, None, None, None, tuple(reasons + ["below threshold"]))

        stop_distance = max(local_atr * 1.2, abs(float(last["high"] - last["low"])) * 1.1)
        if bias is Side.BUY:
            stop_loss = last_close - stop_distance
            take_profit = last_close + (stop_distance * self.config.min_rr)
        else:
            stop_loss = last_close + stop_distance
            take_profit = last_close - (stop_distance * self.config.min_rr)

        return TradeSignal(
            side=bias,
            symbol=symbol,
            confidence=confidence,
            entry=last_close,
            stop_loss=round(stop_loss, 5),
            take_profit=round(take_profit, 5),
            reasons=tuple(reasons),
        )

    @staticmethod
    def _latest_matching(items: Iterable[Any], side: Side) -> Any | None:
        for item in reversed(list(items)):
            if item.side is side:
                return item
        return None


class MT5Gateway:
    def __init__(self, config: TradingConfig) -> None:
        self.config = config

    @property
    def available(self) -> bool:
        return mt5 is not None

    def connect(self) -> None:
        if mt5 is None:
            raise RuntimeError("MetaTrader5 package is not available in this environment.")
        if not mt5.initialize():
            raise RuntimeError(f"MT5 initialize failed: {mt5.last_error()}")
        if not mt5.symbol_select(self.config.symbol, True):
            raise RuntimeError(f"Could not select symbol {self.config.symbol}: {mt5.last_error()}")

    def shutdown(self) -> None:
        if mt5 is not None:
            mt5.shutdown()

    def rates(self) -> pd.DataFrame:
        if mt5 is None:
            raise RuntimeError("MetaTrader5 package is not available.")
        raw = mt5.copy_rates_from_pos(
            self.config.symbol,
            timeframe_value(self.config.timeframe_name),
            0,
            self.config.bars,
        )
        return normalise_rates(raw or [])

    def tick(self) -> Any:
        if mt5 is None:
            return None
        return mt5.symbol_info_tick(self.config.symbol)

    def symbol_info(self) -> Any:
        if mt5 is None:
            return None
        return mt5.symbol_info(self.config.symbol)

    def spread_points(self) -> float | None:
        info = self.symbol_info()
        tick = self.tick()
        if not info or not tick or not getattr(info, "point", None):
            return None
        return abs(float(tick.ask) - float(tick.bid)) / float(info.point)

    def open_positions(self) -> list[Any]:
        if mt5 is None:
            return []
        positions = mt5.positions_get(symbol=self.config.symbol)
        return list(positions or [])

    def order_send(self, signal: TradeSignal, volume: float) -> Any:
        if mt5 is None:
            raise RuntimeError("MetaTrader5 package is not available.")
        if signal.entry is None or signal.stop_loss is None or signal.take_profit is None:
            raise ValueError("Signal must include entry, stop loss, and take profit.")
        order_type = mt5.ORDER_TYPE_BUY if signal.side is Side.BUY else mt5.ORDER_TYPE_SELL
        tick = self.tick()
        price = float(tick.ask if signal.side is Side.BUY else tick.bid)
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
            "comment": "JARVIS_V300_SMC",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        return mt5.order_send(request)

    def modify_stop(self, ticket: int, stop_loss: float, take_profit: float | None) -> Any:
        if mt5 is None:
            raise RuntimeError("MetaTrader5 package is not available.")
        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "position": ticket,
            "symbol": self.config.symbol,
            "sl": stop_loss,
            "tp": take_profit or 0.0,
            "magic": self.config.magic,
        }
        return mt5.order_send(request)


class RiskManager:
    def __init__(self, config: TradingConfig, gateway: MT5Gateway) -> None:
        self.config = config
        self.gateway = gateway

    def volume_for_signal(self, signal: TradeSignal) -> float:
        if signal.entry is None or signal.stop_loss is None:
            return 0.01
        info = self.gateway.symbol_info()
        account = mt5.account_info() if mt5 is not None else None
        if not info or not account:
            return 0.01
        risk_cash = max(0.0, float(account.balance) * self.config.risk_per_trade)
        point = float(info.point)
        tick_value = float(getattr(info, "trade_tick_value", 0.0) or 0.0)
        if point <= 0 or tick_value <= 0 or risk_cash <= 0:
            return float(getattr(info, "volume_min", 0.01) or 0.01)
        stop_points = abs(signal.entry - signal.stop_loss) / point
        if stop_points <= 0:
            return float(getattr(info, "volume_min", 0.01) or 0.01)
        raw_volume = risk_cash / (stop_points * tick_value)
        min_volume = float(getattr(info, "volume_min", 0.01) or 0.01)
        max_volume = float(getattr(info, "volume_max", 1.0) or 1.0)
        step = float(getattr(info, "volume_step", 0.01) or 0.01)
        stepped = math.floor(raw_volume / step) * step
        return round(min(max(stepped, min_volume), max_volume), 2)


class TraderUltimate:
    def __init__(self, config: TradingConfig | None = None) -> None:
        self.config = config or TradingConfig.from_env()
        self.gateway = MT5Gateway(self.config)
        self.analyzer = SMCAnalyzer(self.config)
        self.news = NewsProtection(self.config.news_file, self.config.news_blackout_minutes)
        self.risk = RiskManager(self.config, self.gateway)
        self.paper_positions: list[PaperPosition] = []
        self.config.log_path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> None:
        self.gateway.connect()

    def generate_signal(self, df: pd.DataFrame | None = None) -> TradeSignal:
        if df is None:
            df = self.gateway.rates()
        blocked, news_reason = self.news.blocked(self.config.symbol)
        return self.analyzer.build_signal(
            df,
            self.config.symbol,
            spread_points=self.gateway.spread_points(),
            news_reason=news_reason if blocked else None,
        )

    def execute_signal(self, signal: TradeSignal) -> dict[str, Any]:
        self._log_signal(signal)
        if signal.side is Side.HOLD or signal.entry is None:
            return {"status": "ignored", "reason": "hold or incomplete signal"}
        if signal.confidence < self.config.confluence_threshold:
            return {"status": "ignored", "reason": "confidence below threshold"}
        if len(self.gateway.open_positions()) >= self.config.max_open_positions:
            return {"status": "ignored", "reason": "max open positions reached"}

        volume = self.risk.volume_for_signal(signal)
        if self.config.paper_trading:
            ticket = f"PAPER-{int(time.time() * 1000)}"
            self.paper_positions.append(PaperPosition(ticket, signal, datetime.now(timezone.utc), volume))
            return {"status": "paper_order", "ticket": ticket, "volume": volume, "signal": asdict(signal)}

        if os.getenv("JARVIS_LIVE_TRADING") != "I_UNDERSTAND_RISK":
            return {
                "status": "blocked",
                "reason": "live trading requires JARVIS_LIVE_TRADING=I_UNDERSTAND_RISK",
            }
        result = self.gateway.order_send(signal, volume)
        return {"status": "sent", "volume": volume, "result": str(result)}

    def apply_trailing_stops(self) -> list[dict[str, Any]]:
        if self.config.paper_trading or mt5 is None:
            return []
        df = self.gateway.rates()
        if df.empty:
            return []
        local_atr = float(atr(df, self.config.atr_period).iloc[-1])
        tick = self.gateway.tick()
        if not tick or local_atr <= 0:
            return []
        updates: list[dict[str, Any]] = []
        for position in self.gateway.open_positions():
            current_price = float(tick.bid if position.type == mt5.POSITION_TYPE_BUY else tick.ask)
            if position.type == mt5.POSITION_TYPE_BUY:
                candidate_sl = current_price - self.config.trail_atr_multiple * local_atr
                should_update = candidate_sl > float(position.sl or 0)
            else:
                candidate_sl = current_price + self.config.trail_atr_multiple * local_atr
                should_update = position.sl == 0 or candidate_sl < float(position.sl)
            if should_update:
                result = self.gateway.modify_stop(int(position.ticket), round(candidate_sl, 5), position.tp)
                updates.append({"ticket": position.ticket, "new_sl": round(candidate_sl, 5), "result": str(result)})
        return updates

    def run_once(self) -> dict[str, Any]:
        signal = self.generate_signal()
        execution = self.execute_signal(signal)
        trailing = self.apply_trailing_stops()
        return {"signal": asdict(signal), "execution": execution, "trailing": trailing}

    def loop(self, interval_seconds: float = 10.0) -> None:
        while True:
            try:
                result = self.run_once()
                LOGGER.info("Cycle result: %s", result)
            except KeyboardInterrupt:
                raise
            except Exception:
                LOGGER.exception("Trading cycle failed")
            time.sleep(interval_seconds)

    def _log_signal(self, signal: TradeSignal) -> None:
        with self.config.log_path.open("a", encoding="utf-8") as handle:
            handle.write(signal.to_json() + "\n")


def demo_rates(rows: int = 240) -> pd.DataFrame:
    rng = np.random.default_rng(300)
    base = 1.0800 + np.cumsum(rng.normal(0, 0.00008, size=rows))
    opens = base + rng.normal(0, 0.00003, size=rows)
    closes = base + rng.normal(0, 0.00003, size=rows)
    highs = np.maximum(opens, closes) + rng.uniform(0.00002, 0.00012, size=rows)
    lows = np.minimum(opens, closes) - rng.uniform(0.00002, 0.00012, size=rows)
    now = datetime.now(timezone.utc)
    return pd.DataFrame(
        {
            "time": [now - timedelta(minutes=rows - idx) for idx in range(rows)],
            "open": opens,
            "high": highs,
            "low": lows,
            "close": closes,
            "tick_volume": rng.integers(50, 250, size=rows),
            "spread": rng.integers(8, 25, size=rows),
        }
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="JARVIS Trading-Ultima SMC engine")
    parser.add_argument("--demo", action="store_true", help="Run against generated demo candles")
    parser.add_argument("--loop", action="store_true", help="Run continuously")
    parser.add_argument("--interval", type=float, default=10.0, help="Loop interval in seconds")
    args = parser.parse_args()

    setup_logging()
    engine = TraderUltimate()
    if args.demo:
        signal = engine.generate_signal(demo_rates())
        print(signal.to_json())
        return 0
    engine.connect()
    try:
        if args.loop:
            engine.loop(args.interval)
        else:
            print(json.dumps(engine.run_once(), default=str, indent=2))
    finally:
        engine.gateway.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
