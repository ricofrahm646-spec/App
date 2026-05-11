from __future__ import annotations

import json
import logging
import math
import os
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import requests

try:
    import MetaTrader5 as mt5
except Exception:  # pragma: no cover - optional dependency
    mt5 = None


BASE_DIR = Path(__file__).resolve().parent
RUNTIME_DIR = BASE_DIR / "runtime"
TRADING_STATE_FILE = RUNTIME_DIR / "trading_snapshot.json"
RUNTIME_DIR.mkdir(parents=True, exist_ok=True)

LOGGER = logging.getLogger("jarvis.trader")
if not LOGGER.handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


@dataclass
class TradingConfig:
    symbols: list[str] = field(default_factory=lambda: ["EURUSD", "GBPUSD", "XAUUSD"])
    bars: int = 240
    timeframe: int = getattr(mt5, "TIMEFRAME_M1", 1) if mt5 else 1
    risk_per_trade: float = 0.01
    reward_risk_ratio: float = 1.8
    confluence_threshold: int = 90
    max_spread_points: float = 35.0
    news_guard_minutes: int = 20
    trail_atr_multiplier: float = 0.75
    paper_balance: float = 1000.0
    sl_atr_buffer: float = 0.40
    deviation: int = 8
    magic: int = 300300
    live_trading: bool = field(
        default_factory=lambda: os.getenv("JARVIS_ENABLE_LIVE_TRADING", "0") == "1"
    )
    mt5_path: str | None = field(default_factory=lambda: os.getenv("MT5_TERMINAL_PATH"))


@dataclass
class SignalResult:
    symbol: str
    side: str
    confluence: int
    entry: float
    stop_loss: float
    take_profit: float
    reason: str
    factors: dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        for key in ("entry", "stop_loss", "take_profit"):
            payload[key] = round(float(payload[key]), 6)
        return payload


class NewsProtection:
    CALENDAR_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.xml"
    IMPACT_TOKENS = {"high", "red", "holiday"}

    def __init__(self, guard_minutes: int = 20) -> None:
        self.guard_minutes = guard_minutes
        self.cached_events: list[dict[str, Any]] = []
        self.last_refresh: datetime | None = None

    def _extract_text(self, item: ET.Element, tag: str) -> str:
        node = item.find(tag)
        if node is None or node.text is None:
            return ""
        return node.text.strip()

    def fetch_events(self, force: bool = False) -> list[dict[str, Any]]:
        now = datetime.now(timezone.utc)
        if not force and self.last_refresh and now - self.last_refresh < timedelta(minutes=30):
            return self.cached_events

        try:
            response = requests.get(self.CALENDAR_URL, timeout=10)
            response.raise_for_status()
            root = ET.fromstring(response.text)
            events: list[dict[str, Any]] = []
            for item in root.findall(".//item"):
                title = self._extract_text(item, "title")
                description = self._extract_text(item, "description")
                pub_date_raw = self._extract_text(item, "pubDate")
                if not pub_date_raw:
                    continue
                event_time = parsedate_to_datetime(pub_date_raw)
                if event_time.tzinfo is None:
                    event_time = event_time.replace(tzinfo=timezone.utc)
                impact_text = f"{title} {description}".lower()
                impact = "high" if any(token in impact_text for token in self.IMPACT_TOKENS) else "medium"
                events.append(
                    {
                        "title": title,
                        "description": description,
                        "impact": impact,
                        "time": event_time.astimezone(timezone.utc),
                    }
                )
            self.cached_events = events
            self.last_refresh = now
        except Exception as exc:  # pragma: no cover - network dependent
            LOGGER.warning("Economic calendar refresh failed: %s", exc)
            self.cached_events = self.cached_events or []
            self.last_refresh = now
        return self.cached_events

    def blocks_symbol(self, symbol: str) -> tuple[bool, list[dict[str, Any]]]:
        events = self.fetch_events()
        now = datetime.now(timezone.utc)
        if len(symbol) >= 6:
            currencies = {symbol[:3].upper(), symbol[-3:].upper()}
        else:
            currencies = {symbol[:3].upper()}

        blocking: list[dict[str, Any]] = []
        for event in events:
            if event["impact"] != "high":
                continue
            event_text = f"{event['title']} {event['description']}".upper()
            if not any(currency in event_text for currency in currencies):
                continue
            if abs((event["time"] - now).total_seconds()) <= self.guard_minutes * 60:
                blocking.append(
                    {
                        "title": event["title"],
                        "impact": event["impact"],
                        "time": event["time"].isoformat(),
                    }
                )
        return bool(blocking), blocking


class TradingEngine:
    def __init__(self, config: TradingConfig | None = None) -> None:
        self.config = config or TradingConfig()
        self.news = NewsProtection(self.config.news_guard_minutes)
        self.initialized = False
        self.paper_balance = self.config.paper_balance
        self.paper_positions: list[dict[str, Any]] = []
        self.logs: list[str] = []
        self.equity_curve: list[dict[str, Any]] = []
        self._load_state()

    def _log(self, message: str) -> None:
        line = f"{datetime.now(timezone.utc).isoformat()} | {message}"
        self.logs.append(line)
        self.logs = self.logs[-120:]
        LOGGER.info(message)

    def _load_state(self) -> None:
        if not TRADING_STATE_FILE.exists():
            return
        try:
            payload = json.loads(TRADING_STATE_FILE.read_text(encoding="utf-8"))
            self.paper_balance = float(payload.get("balance", self.paper_balance))
            self.paper_positions = payload.get("positions", [])
            self.logs = payload.get("logs", [])
            self.equity_curve = payload.get("equity_curve", [])
        except Exception as exc:
            self._log(f"Trading state reset after read error: {exc}")

    def initialize(self) -> bool:
        if not self.config.live_trading:
            self._log("Live trading disabled. Engine running in paper mode.")
            return False
        if mt5 is None:
            self._log("MetaTrader5 package unavailable. Falling back to paper mode.")
            return False
        if self.initialized:
            return True

        kwargs: dict[str, Any] = {}
        if self.config.mt5_path:
            kwargs["path"] = self.config.mt5_path
        self.initialized = bool(mt5.initialize(**kwargs))
        if self.initialized:
            self._log("MT5 initialized successfully.")
        else:
            self._log(f"MT5 initialize failed: {mt5.last_error()}")
        return self.initialized

    def shutdown(self) -> None:
        if self.initialized and mt5 is not None:
            mt5.shutdown()
            self.initialized = False

    def _synthetic_rates(self, symbol: str, bars: int) -> pd.DataFrame:
        anchor = 1900.0 if "XAU" in symbol else 1.10 + (sum(ord(ch) for ch in symbol) % 7) * 0.01
        seed = int(datetime.now(timezone.utc).strftime("%Y%m%d%H")) + sum(ord(ch) for ch in symbol)
        rng = np.random.default_rng(seed)
        timestamps = pd.date_range(end=datetime.now(timezone.utc), periods=bars, freq="1min")
        drift = rng.normal(0.0, 0.0005 if "XAU" not in symbol else 0.35, bars).cumsum()
        seasonal = np.sin(np.linspace(0, 12, bars)) * (0.0015 if "XAU" not in symbol else 0.8)
        close = anchor + drift + seasonal
        open_ = np.roll(close, 1)
        open_[0] = close[0]
        spread = np.abs(rng.normal(0.0006 if "XAU" not in symbol else 0.45, 0.0002, bars))
        high = np.maximum(open_, close) + spread
        low = np.minimum(open_, close) - spread
        volume = rng.integers(75, 400, size=bars)
        return pd.DataFrame(
            {
                "time": timestamps,
                "open": open_,
                "high": high,
                "low": low,
                "close": close,
                "tick_volume": volume,
                "real_volume": volume,
                "spread": rng.integers(8, 30, size=bars),
            }
        )

    def fetch_rates(self, symbol: str, bars: int | None = None) -> pd.DataFrame:
        bars = bars or self.config.bars
        if self.initialize() and mt5 is not None:
            rates = mt5.copy_rates_from_pos(symbol, self.config.timeframe, 0, bars)
            if rates is not None and len(rates) >= 50:
                frame = pd.DataFrame(rates)
                frame["time"] = pd.to_datetime(frame["time"], unit="s", utc=True)
                return frame
            self._log(f"Using synthetic feed for {symbol}; MT5 did not return enough bars.")
        return self._synthetic_rates(symbol, bars)

    def _atr(self, frame: pd.DataFrame, period: int = 14) -> pd.Series:
        high_low = frame["high"] - frame["low"]
        high_close = (frame["high"] - frame["close"].shift(1)).abs()
        low_close = (frame["low"] - frame["close"].shift(1)).abs()
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        return true_range.rolling(period).mean().bfill()

    def _prepare_frame(self, frame: pd.DataFrame) -> pd.DataFrame:
        frame = frame.copy()
        frame["ema_fast"] = frame["close"].ewm(span=12, adjust=False).mean()
        frame["ema_slow"] = frame["close"].ewm(span=34, adjust=False).mean()
        frame["atr"] = self._atr(frame)
        frame["body"] = frame["close"] - frame["open"]
        frame["candle_range"] = frame["high"] - frame["low"]
        frame["avg_volume"] = frame["tick_volume"].rolling(20).mean().bfill()
        pivot_window = 7
        frame["swing_high"] = (
            frame["high"] == frame["high"].rolling(pivot_window, center=True).max()
        ).fillna(False)
        frame["swing_low"] = (
            frame["low"] == frame["low"].rolling(pivot_window, center=True).min()
        ).fillna(False)
        frame["bull_fvg"] = frame["low"] > frame["high"].shift(2)
        frame["bear_fvg"] = frame["high"] < frame["low"].shift(2)
        frame["bull_gap_low"] = frame["high"].shift(2)
        frame["bull_gap_high"] = frame["low"]
        frame["bear_gap_low"] = frame["high"]
        frame["bear_gap_high"] = frame["low"].shift(2)
        return frame.dropna().reset_index(drop=True)

    def _regime(self, frame: pd.DataFrame) -> str:
        last = frame.iloc[-1]
        if last["ema_fast"] > last["ema_slow"] and last["close"] >= last["ema_fast"]:
            return "BUY"
        if last["ema_fast"] < last["ema_slow"] and last["close"] <= last["ema_fast"]:
            return "SELL"
        return "NEUTRAL"

    def _spread_points(self, symbol: str, frame: pd.DataFrame) -> float:
        if self.initialized and mt5 is not None:
            tick = mt5.symbol_info_tick(symbol)
            info = mt5.symbol_info(symbol)
            if tick and info and info.point:
                return abs(tick.ask - tick.bid) / info.point
        if "spread" in frame.columns:
            return float(frame["spread"].iloc[-1])
        denominator = 0.01 if "XAU" in symbol else 0.0001
        return float(frame["candle_range"].tail(8).median() / denominator)

    def _session_bonus(self) -> int:
        hour = datetime.now(timezone.utc).hour
        if 6 <= hour <= 10 or 12 <= hour <= 16:
            return 5
        if 0 <= hour <= 2:
            return 2
        return 0

    def _liquidity_sweep(self, frame: pd.DataFrame) -> dict[str, bool]:
        last = frame.iloc[-1]
        prior = frame.iloc[:-1]
        recent_highs = prior.loc[prior["swing_high"], "high"].tail(5)
        recent_lows = prior.loc[prior["swing_low"], "low"].tail(5)
        latest_swing_high = float(recent_highs.max()) if not recent_highs.empty else float(prior["high"].tail(20).max())
        latest_swing_low = float(recent_lows.min()) if not recent_lows.empty else float(prior["low"].tail(20).min())
        return {
            "BUY": bool(last["low"] < latest_swing_low and last["close"] > latest_swing_low),
            "SELL": bool(last["high"] > latest_swing_high and last["close"] < latest_swing_high),
        }

    def _last_fvg(self, frame: pd.DataFrame, side: str) -> dict[str, float] | None:
        if side == "BUY":
            candidate = frame.loc[frame["bull_fvg"]].tail(1)
            if candidate.empty:
                return None
            row = candidate.iloc[-1]
            return {"low": float(row["bull_gap_low"]), "high": float(row["bull_gap_high"])}
        candidate = frame.loc[frame["bear_fvg"]].tail(1)
        if candidate.empty:
            return None
        row = candidate.iloc[-1]
        return {"low": float(row["bear_gap_low"]), "high": float(row["bear_gap_high"])}

    def _order_block(self, frame: pd.DataFrame, side: str) -> dict[str, float] | None:
        window = frame.tail(25)
        if side == "BUY":
            opposite = window[window["close"] < window["open"]]
        else:
            opposite = window[window["close"] > window["open"]]
        if opposite.empty:
            return None
        row = opposite.iloc[-1]
        return {
            "low": float(row["low"]),
            "high": float(row["high"]),
            "mid": float((row["low"] + row["high"]) / 2),
        }

    def _price_inside_zone(self, price: float, zone: dict[str, float] | None, atr: float) -> bool:
        if not zone:
            return False
        low = min(zone["low"], zone["high"]) - atr * 0.2
        high = max(zone["low"], zone["high"]) + atr * 0.2
        return low <= price <= high

    def _market_structure_shift(self, frame: pd.DataFrame, side: str) -> bool:
        last = frame.iloc[-1]
        prior = frame.iloc[:-1].tail(20)
        if side == "BUY":
            reference = float(prior["high"].max())
            return bool(last["close"] > reference)
        reference = float(prior["low"].min())
        return bool(last["close"] < reference)

    def _build_signal(self, symbol: str, side: str, frame: pd.DataFrame) -> SignalResult:
        last = frame.iloc[-1]
        atr = float(last["atr"])
        regime = self._regime(frame)
        sweep = self._liquidity_sweep(frame)
        fvg = self._last_fvg(frame, side)
        order_block = self._order_block(frame, side)
        structure_shift = self._market_structure_shift(frame, side)
        spread_points = self._spread_points(symbol, frame)
        news_blocked, news_events = self.news.blocks_symbol(symbol)
        momentum = (
            last["body"] > 0 and last["tick_volume"] >= last["avg_volume"]
            if side == "BUY"
            else last["body"] < 0 and last["tick_volume"] >= last["avg_volume"]
        )

        score = 0
        factors: dict[str, Any] = {
            "regime": regime,
            "spread_points": round(spread_points, 2),
            "news_blocked": news_blocked,
            "news_events": news_events,
            "atr": round(atr, 6),
        }

        if regime == side:
            score += 15
        if sweep[side]:
            score += 25
            factors["liquidity_sweep"] = True
        if fvg:
            score += 20
            factors["fvg"] = fvg
        if order_block and self._price_inside_zone(float(last["close"]), order_block, atr):
            score += 20
            factors["order_block"] = order_block
        if structure_shift:
            score += 10
            factors["structure_shift"] = True
        if momentum:
            score += 10
            factors["momentum"] = True
        if spread_points <= self.config.max_spread_points:
            score += 5
        score += self._session_bonus()
        score = min(score, 100)

        entry = float(last["close"])
        if side == "BUY":
            stop_reference = min(
                float(last["low"]),
                order_block["low"] if order_block else float(last["low"]),
                fvg["low"] if fvg else float(last["low"]),
            )
            stop_loss = stop_reference - atr * self.config.sl_atr_buffer
            take_profit = entry + (entry - stop_loss) * self.config.reward_risk_ratio
        else:
            stop_reference = max(
                float(last["high"]),
                order_block["high"] if order_block else float(last["high"]),
                fvg["high"] if fvg else float(last["high"]),
            )
            stop_loss = stop_reference + atr * self.config.sl_atr_buffer
            take_profit = entry - (stop_loss - entry) * self.config.reward_risk_ratio

        if news_blocked or score < self.config.confluence_threshold:
            return SignalResult(
                symbol=symbol,
                side="HOLD",
                confluence=score,
                entry=entry,
                stop_loss=stop_loss,
                take_profit=take_profit,
                reason="Confluence below threshold or news guard active.",
                factors=factors,
            )

        return SignalResult(
            symbol=symbol,
            side=side,
            confluence=score,
            entry=entry,
            stop_loss=stop_loss,
            take_profit=take_profit,
            reason="SMC confluence aligned with regime, liquidity sweep and execution filters.",
            factors=factors,
        )

    def analyze_symbol(self, symbol: str) -> SignalResult:
        frame = self._prepare_frame(self.fetch_rates(symbol))
        buy_signal = self._build_signal(symbol, "BUY", frame)
        sell_signal = self._build_signal(symbol, "SELL", frame)
        candidates = [buy_signal, sell_signal]
        actionable = [signal for signal in candidates if signal.side != "HOLD"]
        if not actionable:
            return max(candidates, key=lambda signal: signal.confluence)
        return max(actionable, key=lambda signal: signal.confluence)

    def _volume_for_signal(self, symbol: str, entry: float, stop_loss: float) -> float:
        risk_amount = self.paper_balance * self.config.risk_per_trade
        distance = abs(entry - stop_loss)
        if distance <= 0:
            return 0.01
        if self.initialized and mt5 is not None:
            info = mt5.symbol_info(symbol)
            if info and info.point and info.trade_tick_value:
                ticks = distance / info.point
                raw_volume = risk_amount / max(ticks * info.trade_tick_value, 0.01)
                stepped = math.floor(raw_volume / info.volume_step) * info.volume_step
                return float(min(max(stepped, info.volume_min), info.volume_max))
        notional = 100000 if symbol.endswith(("USD", "JPY")) else 100
        raw = risk_amount / max(distance * notional, 0.01)
        return max(round(raw, 2), 0.01)

    def _send_live_order(self, signal: SignalResult) -> dict[str, Any]:
        if mt5 is None:
            return {"status": "error", "message": "MT5 package unavailable."}
        info = mt5.symbol_info(signal.symbol)
        tick = mt5.symbol_info_tick(signal.symbol)
        if not info or not tick:
            return {"status": "error", "message": f"Symbol {signal.symbol} unavailable."}
        if not info.visible:
            mt5.symbol_select(signal.symbol, True)

        order_type = mt5.ORDER_TYPE_BUY if signal.side == "BUY" else mt5.ORDER_TYPE_SELL
        price = tick.ask if signal.side == "BUY" else tick.bid
        volume = self._volume_for_signal(signal.symbol, signal.entry, signal.stop_loss)
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
            "comment": "JARVIS SMC",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        result = mt5.order_send(request)
        if result is None:
            return {"status": "error", "message": "order_send returned None."}
        return {"status": "ok", "result": str(result), "request": request}

    def _open_paper_position(self, signal: SignalResult) -> None:
        volume = self._volume_for_signal(signal.symbol, signal.entry, signal.stop_loss)
        self.paper_positions.append(
            {
                "symbol": signal.symbol,
                "side": signal.side,
                "entry": signal.entry,
                "stop_loss": signal.stop_loss,
                "take_profit": signal.take_profit,
                "trailing_stop": signal.stop_loss,
                "volume": volume,
                "opened_at": signal.timestamp,
                "confluence": signal.confluence,
            }
        )
        self._log(
            f"Paper position opened on {signal.symbol} {signal.side} at {signal.entry:.5f} with volume {volume:.2f}."
        )

    def _paper_profit(self, position: dict[str, Any], price: float) -> float:
        multiplier = 100 if "XAU" in position["symbol"] else 100000
        if position["side"] == "BUY":
            return (price - position["entry"]) * position["volume"] * multiplier
        return (position["entry"] - price) * position["volume"] * multiplier

    def _manage_paper_positions(self) -> list[dict[str, Any]]:
        closed: list[dict[str, Any]] = []
        survivors: list[dict[str, Any]] = []
        for position in self.paper_positions:
            frame = self._prepare_frame(self.fetch_rates(position["symbol"], 80))
            last = frame.iloc[-1]
            price = float(last["close"])
            atr = float(last["atr"])
            if position["side"] == "BUY":
                position["trailing_stop"] = max(
                    position["trailing_stop"],
                    price - atr * self.config.trail_atr_multiplier,
                )
                exit_hit = price <= position["trailing_stop"] or price >= position["take_profit"]
            else:
                position["trailing_stop"] = min(
                    position["trailing_stop"],
                    price + atr * self.config.trail_atr_multiplier,
                )
                exit_hit = price >= position["trailing_stop"] or price <= position["take_profit"]

            if exit_hit:
                pnl = self._paper_profit(position, price)
                self.paper_balance += pnl
                position["closed_at"] = datetime.now(timezone.utc).isoformat()
                position["exit_price"] = round(price, 6)
                position["pnl"] = round(pnl, 2)
                closed.append(position)
                self._log(
                    f"Paper position closed on {position['symbol']} at {price:.5f}. PnL {pnl:.2f}."
                )
            else:
                position["unrealized_pnl"] = round(self._paper_profit(position, price), 2)
                survivors.append(position)
        self.paper_positions = survivors
        return closed

    def execute_signal(self, signal: SignalResult) -> dict[str, Any]:
        if signal.side == "HOLD":
            return {"status": "skipped", "message": "No qualifying signal."}
        if self.config.live_trading and self.initialized:
            result = self._send_live_order(signal)
            self._log(f"Live execution result for {signal.symbol}: {result}")
            return result
        self._open_paper_position(signal)
        return {"status": "paper", "message": f"Paper position opened for {signal.symbol}."}

    def _calculate_equity(self) -> float:
        equity = self.paper_balance
        for position in self.paper_positions:
            frame = self._prepare_frame(self.fetch_rates(position["symbol"], 50))
            price = float(frame.iloc[-1]["close"])
            equity += self._paper_profit(position, price)
        return round(equity, 2)

    def snapshot(self, signals: list[SignalResult], closed_positions: list[dict[str, Any]]) -> dict[str, Any]:
        equity = self._calculate_equity()
        self.equity_curve.append(
            {"time": datetime.now(timezone.utc).isoformat(), "equity": equity}
        )
        self.equity_curve = self.equity_curve[-240:]
        payload = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "mode": "live" if self.config.live_trading and self.initialized else "paper",
            "balance": round(self.paper_balance, 2),
            "equity": equity,
            "signals": [signal.to_dict() for signal in signals],
            "positions": self.paper_positions,
            "closed_positions": closed_positions[-20:],
            "equity_curve": self.equity_curve,
            "logs": self.logs[-60:],
        }
        TRADING_STATE_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return payload

    def run_cycle(self) -> dict[str, Any]:
        signals = [self.analyze_symbol(symbol) for symbol in self.config.symbols]
        actionable = [signal for signal in signals if signal.side != "HOLD"]
        if actionable:
            self.execute_signal(max(actionable, key=lambda signal: signal.confluence))
        closed_positions = self._manage_paper_positions()
        return self.snapshot(signals, closed_positions)


def main() -> None:
    engine = TradingEngine()
    snapshot = engine.run_cycle()
    print(json.dumps(snapshot, indent=2))


if __name__ == "__main__":
    main()
