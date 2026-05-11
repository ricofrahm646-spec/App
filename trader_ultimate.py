"""
J.A.R.V.I.S. V300 — TRADER ULTIMA
MT5 SMC Scalping Engine: Orderblocks, FVG, Liquidity Sweeps, BOS/CHoCH
M1 timeframe with M5 confirmation | Confluence-gated entries

WARNING: Automated trading carries significant financial risk.
         Past performance does not guarantee future results.
         Use at your own risk with capital you can afford to lose.
"""

import json
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional

import numpy as np
import pandas as pd
from loguru import logger

from config.settings import (
    MT5_LOGIN, MT5_PASSWORD, MT5_SERVER, MT5_PATH,
    TRADING, SMC, LOGS_DIR,
)

try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False
    logger.warning("MetaTrader5 not installed — running in simulation mode")


# ── Data Structures ──────────────────────────────────────────────────────────

class Direction(Enum):
    LONG = "BUY"
    SHORT = "SELL"


class SignalStrength(Enum):
    WEAK = "WEAK"
    MODERATE = "MODERATE"
    STRONG = "STRONG"
    ULTRA = "ULTRA"


@dataclass
class SMCZone:
    zone_type: str  # "OB", "FVG", "LIQ"
    direction: Direction
    price_high: float
    price_low: float
    candle_index: int
    strength: float = 0.0
    mitigated: bool = False


@dataclass
class TradeSignal:
    direction: Direction
    entry: float
    stop_loss: float
    take_profit: float
    confluence: float
    strategy: str
    zones: list = field(default_factory=list)
    strength: SignalStrength = SignalStrength.WEAK


@dataclass
class TradeRecord:
    timestamp: str
    symbol: str
    direction: str
    lot: float
    entry: float
    exit: float
    sl: float
    tp: float
    pnl: float
    confluence: float
    strategy: str


# ── SMC Analysis Engine ──────────────────────────────────────────────────────

class SMCEngine:
    """Smart Money Concepts analysis — detects institutional footprints."""

    def __init__(self, params: dict = None):
        self.params = params or SMC

    def detect_orderblocks(self, df: pd.DataFrame) -> list[SMCZone]:
        """Detect Order Blocks: last opposing candle before a strong move."""
        zones = []
        lookback = self.params["ob_lookback"]
        data = df.tail(lookback).reset_index(drop=True)

        for i in range(2, len(data) - 1):
            body_prev = abs(data.loc[i - 1, "close"] - data.loc[i - 1, "open"])
            body_curr = abs(data.loc[i, "close"] - data.loc[i, "open"])

            if body_curr < 1e-10:
                continue

            move_ratio = body_curr / max(body_prev, 1e-10)

            if (data.loc[i, "close"] > data.loc[i, "open"] and
                    data.loc[i - 1, "close"] < data.loc[i - 1, "open"] and
                    move_ratio > 1.5):
                zones.append(SMCZone(
                    zone_type="OB",
                    direction=Direction.LONG,
                    price_high=data.loc[i - 1, "open"],
                    price_low=data.loc[i - 1, "close"],
                    candle_index=i - 1,
                    strength=min(move_ratio / 3.0, 1.0),
                ))

            if (data.loc[i, "close"] < data.loc[i, "open"] and
                    data.loc[i - 1, "close"] > data.loc[i - 1, "open"] and
                    move_ratio > 1.5):
                zones.append(SMCZone(
                    zone_type="OB",
                    direction=Direction.SHORT,
                    price_high=data.loc[i - 1, "close"],
                    price_low=data.loc[i - 1, "open"],
                    candle_index=i - 1,
                    strength=min(move_ratio / 3.0, 1.0),
                ))

        return zones

    def detect_fvg(self, df: pd.DataFrame) -> list[SMCZone]:
        """Detect Fair Value Gaps: 3-candle imbalances."""
        zones = []
        pip = self._pip_value(df)
        min_gap = self.params["fvg_min_gap_pips"] * pip
        data = df.tail(self.params["ob_lookback"]).reset_index(drop=True)

        for i in range(1, len(data) - 1):
            gap_bull = data.loc[i + 1, "low"] - data.loc[i - 1, "high"]
            if gap_bull > min_gap:
                zones.append(SMCZone(
                    zone_type="FVG",
                    direction=Direction.LONG,
                    price_high=data.loc[i + 1, "low"],
                    price_low=data.loc[i - 1, "high"],
                    candle_index=i,
                    strength=min(gap_bull / (min_gap * 3), 1.0),
                ))

            gap_bear = data.loc[i - 1, "low"] - data.loc[i + 1, "high"]
            if gap_bear > min_gap:
                zones.append(SMCZone(
                    zone_type="FVG",
                    direction=Direction.SHORT,
                    price_high=data.loc[i - 1, "low"],
                    price_low=data.loc[i + 1, "high"],
                    candle_index=i,
                    strength=min(gap_bear / (min_gap * 3), 1.0),
                ))

        return zones

    def detect_liquidity_sweeps(self, df: pd.DataFrame) -> list[SMCZone]:
        """Detect Liquidity Sweeps: wicks beyond recent highs/lows that reject."""
        zones = []
        pip = self._pip_value(df)
        threshold = self.params["liquidity_sweep_threshold_pips"] * pip
        lookback = 20
        data = df.tail(self.params["ob_lookback"]).reset_index(drop=True)

        if len(data) < lookback + 2:
            return zones

        for i in range(lookback, len(data)):
            window = data.iloc[i - lookback:i]
            recent_high = window["high"].max()
            recent_low = window["low"].min()

            if (data.loc[i, "high"] > recent_high + threshold and
                    data.loc[i, "close"] < recent_high):
                wick = data.loc[i, "high"] - max(data.loc[i, "open"], data.loc[i, "close"])
                body = abs(data.loc[i, "close"] - data.loc[i, "open"])
                if wick > body * 0.5:
                    zones.append(SMCZone(
                        zone_type="LIQ",
                        direction=Direction.SHORT,
                        price_high=data.loc[i, "high"],
                        price_low=recent_high,
                        candle_index=i,
                        strength=min(wick / (body + 1e-10), 1.0),
                    ))

            if (data.loc[i, "low"] < recent_low - threshold and
                    data.loc[i, "close"] > recent_low):
                wick = min(data.loc[i, "open"], data.loc[i, "close"]) - data.loc[i, "low"]
                body = abs(data.loc[i, "close"] - data.loc[i, "open"])
                if wick > body * 0.5:
                    zones.append(SMCZone(
                        zone_type="LIQ",
                        direction=Direction.LONG,
                        price_high=recent_low,
                        price_low=data.loc[i, "low"],
                        candle_index=i,
                        strength=min(wick / (body + 1e-10), 1.0),
                    ))

        return zones

    def detect_bos(self, df: pd.DataFrame) -> Optional[Direction]:
        """Break of Structure: trend continuation signal."""
        data = df.tail(self.params["bos_lookback"]).reset_index(drop=True)
        if len(data) < 5:
            return None

        highs = data["high"].values
        lows = data["low"].values
        mid = len(data) // 2

        left_high = highs[:mid].max()
        right_high = highs[mid:].max()
        left_low = lows[:mid].min()
        right_low = lows[mid:].min()

        if right_high > left_high and right_low > left_low:
            return Direction.LONG
        if right_low < left_low and right_high < left_high:
            return Direction.SHORT
        return None

    def detect_choch(self, df: pd.DataFrame) -> Optional[Direction]:
        """Change of Character: trend reversal signal."""
        data = df.tail(self.params["choch_lookback"]).reset_index(drop=True)
        if len(data) < 10:
            return None

        q1 = len(data) // 3
        q3 = 2 * len(data) // 3

        trend_start = data.iloc[:q1]["close"].mean()
        trend_mid = data.iloc[q1:q3]["close"].mean()
        trend_end = data.iloc[q3:]["close"].mean()

        if trend_start < trend_mid and trend_end < trend_mid:
            return Direction.SHORT
        if trend_start > trend_mid and trend_end > trend_mid:
            return Direction.LONG
        return None

    def calculate_confluence(self, direction: Direction, zones: list[SMCZone],
                             bos: Optional[Direction], choch: Optional[Direction]) -> float:
        matching_zones = [z for z in zones if z.direction == direction]
        if not matching_zones:
            return 0.0

        score = 0.0
        zone_types_found = set()

        for z in matching_zones:
            if z.zone_type not in zone_types_found:
                weight = {"OB": 0.30, "FVG": 0.25, "LIQ": 0.25}.get(z.zone_type, 0.1)
                score += weight * z.strength
                zone_types_found.add(z.zone_type)

        if bos == direction:
            score += 0.15
        if choch == direction:
            score += 0.15

        multi_zone_bonus = min(len(zone_types_found) * 0.05, 0.10)
        score += multi_zone_bonus

        return min(score, 1.0)

    @staticmethod
    def _pip_value(df: pd.DataFrame) -> float:
        price = df["close"].iloc[-1] if not df.empty else 1.0
        if price > 50:
            return 0.01
        return 0.0001


# ── Risk Manager ─────────────────────────────────────────────────────────────

class RiskManager:
    def __init__(self):
        self.daily_pnl = 0.0
        self.daily_trades = 0
        self.daily_reset_date = datetime.now().date()

    def _reset_if_new_day(self):
        today = datetime.now().date()
        if today != self.daily_reset_date:
            self.daily_pnl = 0.0
            self.daily_trades = 0
            self.daily_reset_date = today

    def can_trade(self, equity: float) -> tuple[bool, str]:
        self._reset_if_new_day()

        max_daily_loss = equity * (TRADING["max_daily_loss_pct"] / 100)
        if self.daily_pnl < -max_daily_loss:
            return False, f"Daily loss limit reached: €{self.daily_pnl:.2f}"

        return True, "OK"

    def calculate_lot_size(self, equity: float, entry: float, sl: float) -> float:
        risk_amount = equity * (TRADING["max_risk_pct"] / 100)
        sl_distance = abs(entry - sl)
        if sl_distance < 1e-10:
            return TRADING["lot_size_start"]

        pip_val = 0.0001 if entry < 50 else 0.01
        sl_pips = sl_distance / pip_val
        pip_value_per_lot = 10.0

        lot = risk_amount / (sl_pips * pip_value_per_lot)
        lot = max(TRADING["lot_size_start"], min(lot, 1.0))
        return round(lot, 2)

    def record_trade(self, pnl: float):
        self.daily_pnl += pnl
        self.daily_trades += 1


# ── MT5 Connector ────────────────────────────────────────────────────────────

class MT5Connector:
    def __init__(self):
        self.connected = False
        self.sim_mode = not MT5_AVAILABLE

    def connect(self) -> bool:
        if self.sim_mode:
            logger.info("MT5 Simulation Mode — no real connection")
            self.connected = True
            return True

        if not mt5.initialize(path=MT5_PATH):
            logger.error(f"MT5 init failed: {mt5.last_error()}")
            return False

        if MT5_LOGIN and MT5_PASSWORD and MT5_SERVER:
            auth = mt5.login(MT5_LOGIN, password=MT5_PASSWORD, server=MT5_SERVER)
            if not auth:
                logger.error(f"MT5 login failed: {mt5.last_error()}")
                return False

        self.connected = True
        logger.info("MT5 connected successfully")
        return True

    def disconnect(self):
        if not self.sim_mode and MT5_AVAILABLE:
            mt5.shutdown()
        self.connected = False

    def get_rates(self, symbol: str, timeframe: str, count: int) -> pd.DataFrame:
        if self.sim_mode:
            return self._generate_sim_data(symbol, count)

        tf_map = {
            "M1": mt5.TIMEFRAME_M1, "M5": mt5.TIMEFRAME_M5,
            "M15": mt5.TIMEFRAME_M15, "H1": mt5.TIMEFRAME_H1,
            "H4": mt5.TIMEFRAME_H4, "D1": mt5.TIMEFRAME_D1,
        }
        mt5_tf = tf_map.get(timeframe, mt5.TIMEFRAME_M1)
        rates = mt5.copy_rates_from_pos(symbol, mt5_tf, 0, count)

        if rates is None or len(rates) == 0:
            logger.warning(f"No rates for {symbol} {timeframe}")
            return pd.DataFrame()

        df = pd.DataFrame(rates)
        df["time"] = pd.to_datetime(df["time"], unit="s")
        return df

    def get_tick(self, symbol: str) -> dict:
        if self.sim_mode:
            base = 1.0850 + np.random.randn() * 0.001
            spread = np.random.uniform(0.00005, 0.00015)
            return {"bid": base, "ask": base + spread, "time": datetime.now()}

        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            return {"bid": 0, "ask": 0, "time": datetime.now()}
        return {"bid": tick.bid, "ask": tick.ask, "time": datetime.now()}

    def place_order(self, symbol: str, direction: Direction, lot: float,
                    sl: float, tp: float) -> Optional[int]:
        if self.sim_mode:
            ticket = int(time.time() * 1000) % 10_000_000
            logger.info(f"[SIM] Order placed: {direction.value} {lot} {symbol} SL={sl:.5f} TP={tp:.5f} ticket={ticket}")
            return ticket

        tick = self.get_tick(symbol)
        price = tick["ask"] if direction == Direction.LONG else tick["bid"]

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": lot,
            "type": mt5.ORDER_TYPE_BUY if direction == Direction.LONG else mt5.ORDER_TYPE_SELL,
            "price": price,
            "sl": sl,
            "tp": tp,
            "deviation": TRADING["slippage"],
            "magic": 300300,
            "comment": "JARVIS_V300",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        result = mt5.order_send(request)
        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            err = result.retcode if result else "None"
            logger.error(f"Order failed: {err}")
            return None

        logger.info(f"Order placed: ticket={result.order}")
        return result.order

    def modify_sl(self, ticket: int, symbol: str, new_sl: float) -> bool:
        if self.sim_mode:
            logger.info(f"[SIM] Trail SL modified: ticket={ticket} new_sl={new_sl:.5f}")
            return True

        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "position": ticket,
            "symbol": symbol,
            "sl": new_sl,
        }
        result = mt5.order_send(request)
        return result is not None and result.retcode == mt5.TRADE_RETCODE_DONE

    def close_position(self, ticket: int, symbol: str, lot: float,
                       direction: Direction) -> bool:
        if self.sim_mode:
            logger.info(f"[SIM] Position closed: ticket={ticket}")
            return True

        tick = self.get_tick(symbol)
        close_price = tick["bid"] if direction == Direction.LONG else tick["ask"]
        close_type = mt5.ORDER_TYPE_SELL if direction == Direction.LONG else mt5.ORDER_TYPE_BUY

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": lot,
            "type": close_type,
            "position": ticket,
            "price": close_price,
            "deviation": TRADING["slippage"],
            "magic": 300300,
            "comment": "JARVIS_V300_CLOSE",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        result = mt5.order_send(request)
        return result is not None and result.retcode == mt5.TRADE_RETCODE_DONE

    @staticmethod
    def _generate_sim_data(symbol: str, count: int) -> pd.DataFrame:
        np.random.seed(int(time.time()) % 10000)
        base = 1.0850
        returns = np.random.randn(count) * 0.0003
        close = base + np.cumsum(returns)
        high = close + np.abs(np.random.randn(count) * 0.0002)
        low = close - np.abs(np.random.randn(count) * 0.0002)
        opn = close + np.random.randn(count) * 0.00015
        vol = np.random.randint(50, 500, count)
        now = datetime.now()
        times = [now - timedelta(minutes=count - i) for i in range(count)]

        return pd.DataFrame({
            "time": times, "open": opn, "high": high,
            "low": low, "close": close,
            "tick_volume": vol, "spread": np.random.randint(5, 15, count),
        })


# ── News Protection ──────────────────────────────────────────────────────────

class NewsProtection:
    """Block trading around high-impact news events."""

    def __init__(self):
        self.blackout_minutes = TRADING["news_blackout_minutes"]
        self._blocked_windows: list[tuple[datetime, datetime]] = []

    def add_event(self, event_time: datetime):
        start = event_time - timedelta(minutes=self.blackout_minutes)
        end = event_time + timedelta(minutes=self.blackout_minutes)
        self._blocked_windows.append((start, end))

    def is_safe(self) -> tuple[bool, str]:
        now = datetime.now()
        for start, end in self._blocked_windows:
            if start <= now <= end:
                return False, f"News blackout until {end.strftime('%H:%M')}"
        return True, "Clear"


# ── Trail Stop Manager ───────────────────────────────────────────────────────

class TrailStopManager:
    def __init__(self, connector: MT5Connector):
        self.connector = connector
        self.positions: dict[int, dict] = {}

    def register(self, ticket: int, direction: Direction, entry: float, initial_sl: float):
        self.positions[ticket] = {
            "direction": direction,
            "entry": entry,
            "current_sl": initial_sl,
            "highest": entry if direction == Direction.LONG else entry,
            "lowest": entry if direction == Direction.SHORT else entry,
        }

    def update(self, symbol: str):
        tick = self.connector.get_tick(symbol)
        if tick["bid"] == 0:
            return

        current_price = tick["bid"]
        atr_trail = TRADING["trail_stop_atr_mult"] * 0.0005

        for ticket, pos in list(self.positions.items()):
            if pos["direction"] == Direction.LONG:
                if current_price > pos["highest"]:
                    pos["highest"] = current_price
                    new_sl = current_price - atr_trail
                    if new_sl > pos["current_sl"]:
                        if self.connector.modify_sl(ticket, symbol, new_sl):
                            pos["current_sl"] = new_sl
                            logger.info(f"Trail SL raised: ticket={ticket} sl={new_sl:.5f}")
            else:
                if current_price < pos["lowest"]:
                    pos["lowest"] = current_price
                    new_sl = current_price + atr_trail
                    if new_sl < pos["current_sl"]:
                        if self.connector.modify_sl(ticket, symbol, new_sl):
                            pos["current_sl"] = new_sl
                            logger.info(f"Trail SL lowered: ticket={ticket} sl={new_sl:.5f}")

    def remove(self, ticket: int):
        self.positions.pop(ticket, None)


# ── Main Trading Engine ──────────────────────────────────────────────────────

class TraderUltimate:
    def __init__(self):
        self.connector = MT5Connector()
        self.smc = SMCEngine()
        self.risk = RiskManager()
        self.news = NewsProtection()
        self.trail = TrailStopManager(self.connector)
        self.running = False
        self.equity = 10.0
        self.trade_history: list[TradeRecord] = []
        self._thread: Optional[threading.Thread] = None

    def start(self):
        if not self.connector.connect():
            logger.error("Cannot start — MT5 connection failed")
            return False

        self.running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        logger.info("TraderUltimate engine started — Sir, we are live.")
        return True

    def stop(self):
        self.running = False
        if self._thread:
            self._thread.join(timeout=10)
        self.connector.disconnect()
        logger.info("TraderUltimate engine stopped.")

    def _loop(self):
        symbol = TRADING["symbol"]
        while self.running:
            try:
                self._tick(symbol)
                self.trail.update(symbol)
                time.sleep(5)
            except Exception as e:
                logger.error(f"Engine error: {e}")
                time.sleep(10)

    def _tick(self, symbol: str):
        can_trade, reason = self.risk.can_trade(self.equity)
        if not can_trade:
            logger.warning(f"Risk block: {reason}")
            return

        news_safe, news_msg = self.news.is_safe()
        if not news_safe:
            logger.info(f"News protection: {news_msg}")
            return

        tick = self.connector.get_tick(symbol)
        spread = (tick["ask"] - tick["bid"]) / 0.0001
        if spread > TRADING["spread_limit_points"]:
            logger.debug(f"Spread too wide: {spread:.1f} pts")
            return

        df_m1 = self.connector.get_rates(symbol, "M1", 100)
        df_m5 = self.connector.get_rates(symbol, "M5", 50)

        if df_m1.empty or df_m5.empty:
            return

        signal = self._analyze(df_m1, df_m5, tick)
        if signal and signal.confluence >= TRADING["confluence_threshold"]:
            self._execute(signal, symbol, tick)

    def _analyze(self, df_m1: pd.DataFrame, df_m5: pd.DataFrame,
                 tick: dict) -> Optional[TradeSignal]:
        obs = self.smc.detect_orderblocks(df_m1)
        fvgs = self.smc.detect_fvg(df_m1)
        liqs = self.smc.detect_liquidity_sweeps(df_m1)
        bos = self.smc.detect_bos(df_m5)
        choch = self.smc.detect_choch(df_m5)

        all_zones = obs + fvgs + liqs
        if not all_zones:
            return None

        current = tick["bid"]

        for direction in [Direction.LONG, Direction.SHORT]:
            confluence = self.smc.calculate_confluence(direction, all_zones, bos, choch)

            if confluence < TRADING["confluence_threshold"]:
                continue

            matching = [z for z in all_zones if z.direction == direction and not z.mitigated]
            if not matching:
                continue

            best_zone = max(matching, key=lambda z: z.strength)

            if direction == Direction.LONG:
                entry = tick["ask"]
                sl = best_zone.price_low - 0.0005
                risk = entry - sl
                tp = entry + risk * 2.0
            else:
                entry = tick["bid"]
                sl = best_zone.price_high + 0.0005
                risk = sl - entry
                tp = entry - risk * 2.0

            zone_types = list({z.zone_type for z in matching})
            strategy = "+".join(zone_types)
            if bos == direction:
                strategy += "+BOS"
            if choch == direction:
                strategy += "+CHoCH"

            strength = SignalStrength.WEAK
            if confluence >= 0.95:
                strength = SignalStrength.ULTRA
            elif confluence >= 0.90:
                strength = SignalStrength.STRONG
            elif confluence >= 0.80:
                strength = SignalStrength.MODERATE

            return TradeSignal(
                direction=direction,
                entry=entry,
                stop_loss=sl,
                take_profit=tp,
                confluence=confluence,
                strategy=strategy,
                zones=matching,
                strength=strength,
            )

        return None

    def _execute(self, signal: TradeSignal, symbol: str, tick: dict):
        lot = self.risk.calculate_lot_size(self.equity, signal.entry, signal.stop_loss)

        logger.info(
            f"SIGNAL [{signal.strength.value}]: {signal.direction.value} {symbol} "
            f"@ {signal.entry:.5f} SL={signal.stop_loss:.5f} TP={signal.take_profit:.5f} "
            f"Confluence={signal.confluence:.1%} Strategy={signal.strategy} Lot={lot}"
        )

        ticket = self.connector.place_order(
            symbol, signal.direction, lot, signal.stop_loss, signal.take_profit,
        )

        if ticket:
            self.trail.register(ticket, signal.direction, signal.entry, signal.stop_loss)

            sim_pnl = 0.0
            if self.connector.sim_mode:
                sim_pnl = np.random.choice(
                    [abs(signal.entry - signal.take_profit), -abs(signal.entry - signal.stop_loss)],
                    p=[0.55, 0.45],
                ) * lot * 100000 * 0.0001
                sim_pnl = round(sim_pnl, 2)
                self.equity += sim_pnl
                self.risk.record_trade(sim_pnl)

            record = TradeRecord(
                timestamp=datetime.now().isoformat(),
                symbol=symbol,
                direction=signal.direction.value,
                lot=lot,
                entry=signal.entry,
                exit=signal.take_profit if sim_pnl >= 0 else signal.stop_loss,
                sl=signal.stop_loss,
                tp=signal.take_profit,
                pnl=sim_pnl,
                confluence=signal.confluence,
                strategy=signal.strategy,
            )
            self.trade_history.append(record)
            self._save_history()
            self._save_equity()

    def _save_history(self):
        path = LOGS_DIR / "trade_history.csv"
        df = pd.DataFrame([asdict(r) for r in self.trade_history])
        df.to_csv(path, index=False)

    def _save_equity(self):
        path = LOGS_DIR / "equity_curve.json"
        entry = {"time": datetime.now().isoformat(), "equity": round(self.equity, 2)}

        data = []
        if path.exists():
            try:
                with open(path) as f:
                    data = json.load(f)
            except Exception:
                pass
        data.append(entry)
        with open(path, "w") as f:
            json.dump(data, f)

    def get_status(self) -> dict:
        wins = sum(1 for t in self.trade_history if t.pnl > 0)
        total = len(self.trade_history)
        return {
            "status": "ACTIVE" if self.running else "STANDBY",
            "last_signal": self.trade_history[-1].strategy if self.trade_history else "—",
            "win_rate": round(wins / total * 100, 1) if total > 0 else 0.0,
            "equity": round(self.equity, 2),
            "trades_today": self.risk.daily_trades,
        }


# ── Entry Point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logger.add(LOGS_DIR / "trader.log", rotation="10 MB", retention="7 days")

    engine = TraderUltimate()
    if engine.start():
        try:
            while True:
                status = engine.get_status()
                logger.info(f"Status: {status}")
                time.sleep(30)
        except KeyboardInterrupt:
            engine.stop()
            logger.info("Sir, trading engine shut down gracefully.")
