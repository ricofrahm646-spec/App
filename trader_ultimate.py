from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import json
import random

import numpy as np
import pandas as pd

try:
    import MetaTrader5 as mt5
except Exception:  # pragma: no cover - optional dependency/runtime
    mt5 = None


@dataclass
class Candle:
    time: datetime
    open: float
    high: float
    low: float
    close: float
    tick_volume: float


@dataclass
class SMCSignal:
    name: str
    direction: str
    strength: float
    confidence: float
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TradeDecision:
    timestamp: datetime
    symbol: str
    direction: str
    confidence: float
    entry: float
    stop_loss: float
    take_profit: float
    reason: str
    signals: List[SMCSignal]


@dataclass
class TradeResult:
    executed: bool
    ticket: Optional[int]
    symbol: str
    direction: str
    volume: float
    entry: float
    stop_loss: float
    take_profit: float
    profit: float = 0.0
    message: str = ""


class NewsProtection:
    """Blocks entries around high-impact events from a local calendar."""

    def __init__(self, calendar_path: str = "news_calendar.json", lock_minutes: int = 15) -> None:
        self.calendar_path = Path(calendar_path)
        self.lock_minutes = lock_minutes
        self._events: List[Dict[str, Any]] = []
        self.reload()

    def reload(self) -> None:
        self._events = []
        if not self.calendar_path.exists():
            return
        try:
            payload = json.loads(self.calendar_path.read_text(encoding="utf-8"))
            for event in payload:
                raw_time = str(event.get("time", "")).strip()
                if not raw_time:
                    continue
                event_time = datetime.fromisoformat(raw_time.replace("Z", "+00:00"))
                if event_time.tzinfo is None:
                    event_time = event_time.replace(tzinfo=timezone.utc)
                self._events.append(
                    {
                        "time": event_time.astimezone(timezone.utc),
                        "currency": event.get("currency", "ALL"),
                        "impact": str(event.get("impact", "low")).lower(),
                        "title": event.get("title", "Unnamed event"),
                    }
                )
        except Exception:
            self._events = []

    def in_lock_window(self, symbol: str, now_utc: Optional[datetime] = None) -> Tuple[bool, List[Dict[str, Any]]]:
        now_utc = now_utc or datetime.now(timezone.utc)
        window = timedelta(minutes=self.lock_minutes)
        related = []
        for event in self._events:
            delta = abs(event["time"] - now_utc)
            if delta <= window and event["impact"] in {"high", "medium"}:
                related.append(event)
        return bool(related), related


class TraderUltimate:
    """SMC-based M1 scalper with MT5 integration and dry-run fallback."""

    def __init__(
        self,
        login: Optional[int] = None,
        password: Optional[str] = None,
        server: Optional[str] = None,
        risk_per_trade: float = 0.02,
        min_confidence: float = 90.0,
        dry_run: Optional[bool] = None,
    ) -> None:
        self.login = login
        self.password = password
        self.server = server
        self.risk_per_trade = risk_per_trade
        self.min_confidence = min_confidence
        self.dry_run = (mt5 is None) if dry_run is None else dry_run
        self.news_guard = NewsProtection()

        self.connected = False
        self.status_log: List[Dict[str, Any]] = []
        self.signal_log: List[Dict[str, Any]] = []
        self.equity_curve: List[Tuple[datetime, float]] = []
        self._sim_balance = 10.0
        self._sim_ticket = 10_000
        self._max_log_items = 400

    def log(self, level: str, message: str, **meta: Any) -> None:
        item = {
            "time": datetime.now(timezone.utc).isoformat(),
            "level": level.upper(),
            "message": message,
            "meta": meta,
        }
        self.status_log.append(item)
        self.status_log = self.status_log[-self._max_log_items :]

    def initialize(self) -> bool:
        if self.dry_run:
            self.connected = True
            self.log("INFO", "Running in dry-run mode (MT5 not required).")
            return True
        if mt5 is None:
            self.log("ERROR", "MetaTrader5 package is unavailable.")
            return False
        kwargs: Dict[str, Any] = {}
        if self.login:
            kwargs["login"] = int(self.login)
        if self.password:
            kwargs["password"] = self.password
        if self.server:
            kwargs["server"] = self.server
        ok = mt5.initialize(**kwargs)
        self.connected = bool(ok)
        if not ok:
            self.log("ERROR", "MT5 initialize failed.", error=mt5.last_error())
        else:
            self.log("INFO", "Connected to MT5 terminal.")
        return self.connected

    def shutdown(self) -> None:
        if self.connected and mt5 is not None and not self.dry_run:
            mt5.shutdown()
        self.connected = False
        self.log("INFO", "Trader shutdown complete.")

    def _ensure_connection(self) -> bool:
        return self.connected or self.initialize()

    def _synthetic_rates(self, bars: int = 400) -> pd.DataFrame:
        rng = np.random.default_rng(7)
        now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
        prices = [1.0800]
        for _ in range(bars - 1):
            prices.append(prices[-1] + float(rng.normal(0, 0.00025)))
        opens, highs, lows, closes, vols, times = [], [], [], [], [], []
        for i, price in enumerate(prices):
            o = price
            c = price + float(rng.normal(0, 0.00015))
            h = max(o, c) + abs(float(rng.normal(0, 0.0001)))
            l = min(o, c) - abs(float(rng.normal(0, 0.0001)))
            t = now - timedelta(minutes=(bars - i))
            opens.append(o)
            highs.append(h)
            lows.append(l)
            closes.append(c)
            vols.append(int(abs(rng.normal(1300, 500))))
            times.append(int(t.timestamp()))
        return pd.DataFrame(
            {
                "time": times,
                "open": opens,
                "high": highs,
                "low": lows,
                "close": closes,
                "tick_volume": vols,
            }
        )

    def fetch_rates(self, symbol: str, bars: int = 400) -> pd.DataFrame:
        if not self._ensure_connection():
            return pd.DataFrame()
        if self.dry_run:
            return self._synthetic_rates(bars=bars)
        assert mt5 is not None
        rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 0, bars)
        if rates is None:
            self.log("ERROR", "Failed to load rates.", symbol=symbol, error=mt5.last_error())
            return pd.DataFrame()
        return pd.DataFrame(rates)

    @staticmethod
    def _to_candles(rates: pd.DataFrame) -> List[Candle]:
        candles: List[Candle] = []
        for _, row in rates.iterrows():
            candles.append(
                Candle(
                    time=datetime.fromtimestamp(int(row["time"]), tz=timezone.utc),
                    open=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    close=float(row["close"]),
                    tick_volume=float(row.get("tick_volume", 0)),
                )
            )
        return candles

    @staticmethod
    def _atr(candles: List[Candle], period: int = 14) -> float:
        if len(candles) < period + 2:
            return max(abs(candles[-1].high - candles[-1].low), 0.0004) if candles else 0.0004
        trs = []
        for i in range(1, len(candles)):
            cur = candles[i]
            prev = candles[i - 1]
            tr = max(cur.high - cur.low, abs(cur.high - prev.close), abs(cur.low - prev.close))
            trs.append(tr)
        tail = trs[-period:]
        return float(np.mean(tail)) if tail else 0.0004

    def _detect_orderblocks(self, candles: List[Candle]) -> List[SMCSignal]:
        signals: List[SMCSignal] = []
        for i in range(2, len(candles)):
            prev = candles[i - 1]
            cur = candles[i]
            prev_body = abs(prev.close - prev.open) + 1e-7
            cur_body = abs(cur.close - cur.open)
            if prev.close < prev.open and cur.close > prev.high and cur_body / prev_body > 1.2:
                signals.append(
                    SMCSignal("ORDERBLOCK_BULLISH", "long", 2.6, 0.88, {"index": i, "price_zone": [prev.low, prev.high]})
                )
            if prev.close > prev.open and cur.close < prev.low and cur_body / prev_body > 1.2:
                signals.append(
                    SMCSignal("ORDERBLOCK_BEARISH", "short", 2.6, 0.88, {"index": i, "price_zone": [prev.low, prev.high]})
                )
        return signals

    def _detect_fvg(self, candles: List[Candle]) -> List[SMCSignal]:
        signals: List[SMCSignal] = []
        for i in range(2, len(candles)):
            c0 = candles[i - 2]
            c1 = candles[i - 1]
            c2 = candles[i]
            if c0.high < c2.low and c1.close > c1.open:
                gap = c2.low - c0.high
                signals.append(SMCSignal("FVG_BULLISH", "long", min(3.2, 1.4 + gap * 10000), 0.92, {"index": i, "gap": gap}))
            if c0.low > c2.high and c1.close < c1.open:
                gap = c0.low - c2.high
                signals.append(
                    SMCSignal("FVG_BEARISH", "short", min(3.2, 1.4 + gap * 10000), 0.92, {"index": i, "gap": gap})
                )
        return signals

    def _detect_liquidity_sweeps(self, candles: List[Candle], lookback: int = 8) -> List[SMCSignal]:
        signals: List[SMCSignal] = []
        if len(candles) < lookback + 2:
            return signals
        for i in range(lookback, len(candles)):
            current = candles[i]
            prev_window = candles[i - lookback : i]
            prior_high = max(c.high for c in prev_window)
            prior_low = min(c.low for c in prev_window)
            if current.high > prior_high and current.close < current.open:
                strength = min(3.0, 1.8 + (current.high - prior_high) * 10000)
                signals.append(SMCSignal("LIQUIDITY_SWEEP_BEARISH", "short", strength, 0.9, {"index": i}))
            if current.low < prior_low and current.close > current.open:
                strength = min(3.0, 1.8 + (prior_low - current.low) * 10000)
                signals.append(SMCSignal("LIQUIDITY_SWEEP_BULLISH", "long", strength, 0.9, {"index": i}))
        return signals

    def _aggregate_decision(self, symbol: str, candles: List[Candle], signals: List[SMCSignal]) -> Optional[TradeDecision]:
        if not candles or not signals:
            return None
        long_score = sum(s.strength * s.confidence for s in signals if s.direction == "long")
        short_score = sum(s.strength * s.confidence for s in signals if s.direction == "short")
        if abs(long_score - short_score) < 0.2:
            return None

        direction = "long" if long_score > short_score else "short"
        dominant_score = max(long_score, short_score)
        confluence = len({s.name.split("_")[0] for s in signals if s.direction == direction})
        confidence = min(99.0, 58.0 + dominant_score * 4.5 + confluence * 7.0)

        entry = candles[-1].close
        atr = self._atr(candles, 14)
        if direction == "long":
            stop_loss = entry - atr * 1.25
            take_profit = entry + (entry - stop_loss) * 2.2
        else:
            stop_loss = entry + atr * 1.25
            take_profit = entry - (stop_loss - entry) * 2.2

        used = [s for s in signals if s.direction == direction][-6:]
        reason = f"SMC confluence={confluence}, score={dominant_score:.2f}, dir={direction}"
        return TradeDecision(
            timestamp=datetime.now(timezone.utc),
            symbol=symbol,
            direction=direction,
            confidence=confidence,
            entry=entry,
            stop_loss=stop_loss,
            take_profit=take_profit,
            reason=reason,
            signals=used,
        )

    def _passes_confluence_gate(self, decision: TradeDecision) -> bool:
        families = {s.name.split("_")[0] for s in decision.signals}
        gate = {"ORDERBLOCK", "FVG", "LIQUIDITY"}.issubset(families) and decision.confidence >= self.min_confidence
        if not gate:
            self.log(
                "INFO",
                "Confluence gate blocked trade.",
                confidence=round(decision.confidence, 2),
                min_confidence=self.min_confidence,
                families=sorted(families),
            )
        return gate

    def evaluate_signal(self, symbol: str) -> Optional[TradeDecision]:
        rates = self.fetch_rates(symbol=symbol, bars=500)
        if rates.empty:
            return None
        candles = self._to_candles(rates)
        signals = self._detect_orderblocks(candles) + self._detect_fvg(candles) + self._detect_liquidity_sweeps(candles)
        decision = self._aggregate_decision(symbol=symbol, candles=candles, signals=signals)
        if decision and self._passes_confluence_gate(decision):
            self.signal_log.append(
                {
                    "time": decision.timestamp.isoformat(),
                    "symbol": decision.symbol,
                    "direction": decision.direction,
                    "confidence": round(decision.confidence, 2),
                    "reason": decision.reason,
                }
            )
            self.signal_log = self.signal_log[-self._max_log_items :]
            return decision
        return None

    def get_balance(self) -> float:
        if self.dry_run:
            return float(self._sim_balance)
        if mt5 is None:
            return 0.0
        info = mt5.account_info()
        return float(getattr(info, "equity", 0.0)) if info else 0.0

    def _position_size(self, symbol: str, entry: float, stop_loss: float) -> float:
        risk_cash = max(self.get_balance() * self.risk_per_trade, 0.2)
        stop_dist = abs(entry - stop_loss)
        if stop_dist <= 1e-9:
            return 0.01
        if self.dry_run or mt5 is None:
            return round(max(0.01, min(2.0, risk_cash / (stop_dist * 10000))), 2)

        info = mt5.symbol_info(symbol)
        if info is None:
            return 0.01
        point = float(getattr(info, "point", 0.0001)) or 0.0001
        contract = float(getattr(info, "trade_contract_size", 100000))
        steps = max(stop_dist / point, 1.0)
        value_per_step = max((point * contract), 0.1)
        lots = risk_cash / (steps * value_per_step)

        min_vol = float(getattr(info, "volume_min", 0.01))
        max_vol = float(getattr(info, "volume_max", 5.0))
        step = float(getattr(info, "volume_step", 0.01)) or 0.01
        lots = max(min_vol, min(max_vol, lots))
        rounded = round(lots / step) * step
        return round(rounded, 2)

    def _blocked_by_news(self, symbol: str) -> Tuple[bool, str]:
        blocked, events = self.news_guard.in_lock_window(symbol)
        if not blocked:
            return False, ""
        snippets = [f"{e['currency']} {e['title']} {e['time'].strftime('%H:%M UTC')}" for e in events[:3]]
        return True, "News lock active: " + " | ".join(snippets)

    def execute_trade(self, decision: TradeDecision) -> TradeResult:
        blocked, reason = self._blocked_by_news(decision.symbol)
        if blocked:
            self.log("WARNING", reason)
            return TradeResult(
                executed=False,
                ticket=None,
                symbol=decision.symbol,
                direction=decision.direction,
                volume=0.0,
                entry=decision.entry,
                stop_loss=decision.stop_loss,
                take_profit=decision.take_profit,
                message=reason,
            )

        volume = self._position_size(decision.symbol, decision.entry, decision.stop_loss)
        if self.dry_run:
            self._sim_ticket += 1
            edge = (decision.confidence - self.min_confidence) / 100.0
            drift = 0.2 + max(edge, -0.15)
            pnl = round(random.uniform(-1.5, 2.8) * drift, 2)
            self._sim_balance += pnl
            self.log("INFO", "Dry-run trade executed.", pnl=pnl, balance=self._sim_balance)
            return TradeResult(
                executed=True,
                ticket=self._sim_ticket,
                symbol=decision.symbol,
                direction=decision.direction,
                volume=volume,
                entry=decision.entry,
                stop_loss=decision.stop_loss,
                take_profit=decision.take_profit,
                profit=pnl,
                message="dry-run",
            )

        if mt5 is None:
            return TradeResult(
                executed=False,
                ticket=None,
                symbol=decision.symbol,
                direction=decision.direction,
                volume=volume,
                entry=decision.entry,
                stop_loss=decision.stop_loss,
                take_profit=decision.take_profit,
                message="MetaTrader5 unavailable",
            )

        if not mt5.symbol_select(decision.symbol, True):
            return TradeResult(
                executed=False,
                ticket=None,
                symbol=decision.symbol,
                direction=decision.direction,
                volume=volume,
                entry=decision.entry,
                stop_loss=decision.stop_loss,
                take_profit=decision.take_profit,
                message="Could not select symbol.",
            )

        tick = mt5.symbol_info_tick(decision.symbol)
        if tick is None:
            return TradeResult(
                executed=False,
                ticket=None,
                symbol=decision.symbol,
                direction=decision.direction,
                volume=volume,
                entry=decision.entry,
                stop_loss=decision.stop_loss,
                take_profit=decision.take_profit,
                message="No live tick available.",
            )

        order_type = mt5.ORDER_TYPE_BUY if decision.direction == "long" else mt5.ORDER_TYPE_SELL
        price = float(tick.ask if decision.direction == "long" else tick.bid)
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": decision.symbol,
            "volume": volume,
            "type": order_type,
            "price": price,
            "sl": float(decision.stop_loss),
            "tp": float(decision.take_profit),
            "deviation": 20,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
            "comment": f"JARVIS-ULTIMA conf={decision.confidence:.1f}",
        }
        result = mt5.order_send(request)
        if result is None:
            return TradeResult(
                executed=False,
                ticket=None,
                symbol=decision.symbol,
                direction=decision.direction,
                volume=volume,
                entry=price,
                stop_loss=decision.stop_loss,
                take_profit=decision.take_profit,
                message="Order send returned None.",
            )
        executed = int(getattr(result, "retcode", 0)) == int(mt5.TRADE_RETCODE_DONE)
        ticket = int(getattr(result, "order", 0)) or None
        message = f"retcode={getattr(result, 'retcode', None)}"
        self.log("INFO" if executed else "ERROR", "MT5 order result.", ticket=ticket, message=message)
        return TradeResult(
            executed=executed,
            ticket=ticket,
            symbol=decision.symbol,
            direction=decision.direction,
            volume=volume,
            entry=price,
            stop_loss=decision.stop_loss,
            take_profit=decision.take_profit,
            message=message,
        )

    def trail_stop(self, symbol: str, atr_multiplier: float = 0.75) -> int:
        if self.dry_run or mt5 is None:
            return 0
        positions = mt5.positions_get(symbol=symbol)
        if not positions:
            return 0
        rates = self.fetch_rates(symbol, bars=120)
        candles = self._to_candles(rates)
        atr = self._atr(candles, period=14)
        modified = 0
        for p in positions:
            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                continue
            if int(p.type) == int(mt5.ORDER_TYPE_BUY):
                candidate = float(tick.bid - atr * atr_multiplier)
                if candidate > float(p.sl):
                    request = {"action": mt5.TRADE_ACTION_SLTP, "position": int(p.ticket), "symbol": symbol, "sl": candidate, "tp": float(p.tp)}
                    out = mt5.order_send(request)
                    if out and int(getattr(out, "retcode", 0)) == int(mt5.TRADE_RETCODE_DONE):
                        modified += 1
            else:
                candidate = float(tick.ask + atr * atr_multiplier)
                if float(p.sl) == 0.0 or candidate < float(p.sl):
                    request = {"action": mt5.TRADE_ACTION_SLTP, "position": int(p.ticket), "symbol": symbol, "sl": candidate, "tp": float(p.tp)}
                    out = mt5.order_send(request)
                    if out and int(getattr(out, "retcode", 0)) == int(mt5.TRADE_RETCODE_DONE):
                        modified += 1
        if modified:
            self.log("INFO", "Trailing stop updated.", symbol=symbol, positions=modified)
        return modified

    def run_cycle(self, symbol: str = "EURUSD") -> Optional[TradeResult]:
        decision = self.evaluate_signal(symbol=symbol)
        if not decision:
            self.log("INFO", "No qualified setup this cycle.", symbol=symbol)
            self.equity_curve.append((datetime.now(timezone.utc), self.get_balance()))
            self.equity_curve = self.equity_curve[-self._max_log_items :]
            return None
        result = self.execute_trade(decision)
        self.equity_curve.append((datetime.now(timezone.utc), self.get_balance()))
        self.equity_curve = self.equity_curve[-self._max_log_items :]
        return result

    def dashboard_snapshot(self) -> Dict[str, Any]:
        return {
            "connected": self.connected,
            "dry_run": self.dry_run,
            "balance": round(self.get_balance(), 2),
            "signals": list(self.signal_log[-50:]),
            "status": list(self.status_log[-100:]),
            "equity_curve": [
                {"time": ts.isoformat(), "equity": value}
                for ts, value in self.equity_curve[-200:]
            ],
        }


if __name__ == "__main__":
    trader = TraderUltimate(dry_run=True, min_confidence=90.0)
    trader.initialize()
    for _ in range(5):
        trader.run_cycle("EURUSD")
    print(json.dumps(trader.dashboard_snapshot(), indent=2))
