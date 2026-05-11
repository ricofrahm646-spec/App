"""
J.A.R.V.I.S. V300 - TRADING ULTIMA ENGINE
Smart Money Concepts (SMC) based M1 Scalping System.

RISK DISCLAIMER: Automated trading carries substantial risk of financial loss.
Past performance does not guarantee future results. Only trade with money you
can afford to lose. This software is provided AS-IS with NO guarantees.
"""
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional

import numpy as np
import pandas as pd

logger = logging.getLogger("JARVIS.Trader")


class Direction(Enum):
    LONG = "BUY"
    SHORT = "SELL"


class SignalStrength(Enum):
    WEAK = "WEAK"
    MODERATE = "MODERATE"
    STRONG = "STRONG"
    ULTRA = "ULTRA"


@dataclass
class OrderBlock:
    high: float
    low: float
    direction: Direction
    timestamp: datetime
    volume: float
    mitigated: bool = False

    @property
    def midpoint(self) -> float:
        return (self.high + self.low) / 2.0


@dataclass
class FairValueGap:
    high: float
    low: float
    direction: Direction
    timestamp: datetime
    filled: bool = False

    @property
    def size(self) -> float:
        return abs(self.high - self.low)


@dataclass
class LiquiditySweep:
    level: float
    direction: Direction
    timestamp: datetime
    swept: bool = False


@dataclass
class TradeSignal:
    direction: Direction
    entry: float
    stop_loss: float
    take_profit: float
    confluence_score: float
    strength: SignalStrength
    reasons: list = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def risk_reward(self) -> float:
        risk = abs(self.entry - self.stop_loss)
        if risk == 0:
            return 0
        return abs(self.take_profit - self.entry) / risk


@dataclass
class TradeRecord:
    ticket: int
    direction: Direction
    entry_price: float
    stop_loss: float
    take_profit: float
    lot_size: float
    open_time: datetime
    close_time: Optional[datetime] = None
    close_price: Optional[float] = None
    profit: float = 0.0
    status: str = "OPEN"


class SMCAnalyzer:
    """Smart Money Concepts analysis engine."""

    def __init__(self, lookback: int = 50, ob_threshold: float = 1.5):
        self.lookback = lookback
        self.ob_threshold = ob_threshold
        self.order_blocks: list[OrderBlock] = []
        self.fvgs: list[FairValueGap] = []
        self.liquidity_levels: list[LiquiditySweep] = []

    def analyze(self, df: pd.DataFrame) -> dict:
        if len(df) < self.lookback:
            return {"order_blocks": [], "fvgs": [], "liquidity": [], "bias": None}

        self._detect_order_blocks(df)
        self._detect_fvgs(df)
        self._detect_liquidity_levels(df)
        bias = self._determine_bias(df)

        return {
            "order_blocks": [ob for ob in self.order_blocks if not ob.mitigated],
            "fvgs": [fvg for fvg in self.fvgs if not fvg.filled],
            "liquidity": [lq for lq in self.liquidity_levels if not lq.swept],
            "bias": bias,
        }

    def _detect_order_blocks(self, df: pd.DataFrame) -> None:
        closes = df["close"].values
        opens = df["open"].values
        highs = df["high"].values
        lows = df["low"].values
        volumes = df["tick_volume"].values if "tick_volume" in df.columns else np.ones(len(df))
        times = df.index if isinstance(df.index, pd.DatetimeIndex) else pd.to_datetime(df["time"])

        avg_body = np.mean(np.abs(closes - opens))

        for i in range(2, len(df) - 1):
            body = abs(closes[i] - opens[i])
            prev_body = abs(closes[i - 1] - opens[i - 1])

            if body < avg_body * self.ob_threshold:
                continue

            is_bullish_engulf = (
                closes[i] > opens[i]
                and closes[i - 1] < opens[i - 1]
                and closes[i] > opens[i - 1]
            )
            is_bearish_engulf = (
                closes[i] < opens[i]
                and closes[i - 1] > opens[i - 1]
                and closes[i] < opens[i - 1]
            )

            if is_bullish_engulf:
                ob = OrderBlock(
                    high=highs[i - 1],
                    low=lows[i - 1],
                    direction=Direction.LONG,
                    timestamp=times[i - 1],
                    volume=volumes[i],
                )
                self.order_blocks.append(ob)

            elif is_bearish_engulf:
                ob = OrderBlock(
                    high=highs[i - 1],
                    low=lows[i - 1],
                    direction=Direction.SHORT,
                    timestamp=times[i - 1],
                    volume=volumes[i],
                )
                self.order_blocks.append(ob)

        self.order_blocks = self.order_blocks[-20:]

    def _detect_fvgs(self, df: pd.DataFrame) -> None:
        highs = df["high"].values
        lows = df["low"].values
        closes = df["close"].values
        opens = df["open"].values
        times = df.index if isinstance(df.index, pd.DatetimeIndex) else pd.to_datetime(df["time"])

        for i in range(2, len(df)):
            if closes[i] > opens[i] and lows[i] > highs[i - 2]:
                fvg = FairValueGap(
                    high=lows[i],
                    low=highs[i - 2],
                    direction=Direction.LONG,
                    timestamp=times[i],
                )
                self.fvgs.append(fvg)

            elif closes[i] < opens[i] and highs[i] < lows[i - 2]:
                fvg = FairValueGap(
                    high=lows[i - 2],
                    low=highs[i],
                    direction=Direction.SHORT,
                    timestamp=times[i],
                )
                self.fvgs.append(fvg)

        self.fvgs = self.fvgs[-20:]

    def _detect_liquidity_levels(self, df: pd.DataFrame) -> None:
        highs = df["high"].values
        lows = df["low"].values
        times = df.index if isinstance(df.index, pd.DatetimeIndex) else pd.to_datetime(df["time"])

        window = min(20, len(df) - 2)

        for i in range(window, len(df) - window):
            if highs[i] == max(highs[i - window:i + window + 1]):
                self.liquidity_levels.append(
                    LiquiditySweep(level=highs[i], direction=Direction.SHORT, timestamp=times[i])
                )

            if lows[i] == min(lows[i - window:i + window + 1]):
                self.liquidity_levels.append(
                    LiquiditySweep(level=lows[i], direction=Direction.LONG, timestamp=times[i])
                )

        self.liquidity_levels = self.liquidity_levels[-20:]

    def _determine_bias(self, df: pd.DataFrame) -> Optional[Direction]:
        closes = df["close"].values
        if len(closes) < 20:
            return None

        ema_fast = pd.Series(closes).ewm(span=9).mean().iloc[-1]
        ema_slow = pd.Series(closes).ewm(span=21).mean().iloc[-1]

        if ema_fast > ema_slow:
            return Direction.LONG
        elif ema_fast < ema_slow:
            return Direction.SHORT
        return None


class ConfluenceEngine:
    """Scores trade setups based on multiple confluences."""

    WEIGHTS = {
        "order_block": 0.25,
        "fvg": 0.20,
        "liquidity_sweep": 0.20,
        "trend_alignment": 0.15,
        "session_time": 0.10,
        "volume_profile": 0.10,
    }

    def __init__(self, config):
        self.config = config

    def score(self, price: float, direction: Direction, smc_data: dict, hour: int) -> TradeSignal:
        scores = {}
        reasons = []

        ob_score = self._score_order_blocks(price, direction, smc_data["order_blocks"])
        scores["order_block"] = ob_score
        if ob_score > 0:
            reasons.append(f"OB confluence: {ob_score:.0%}")

        fvg_score = self._score_fvgs(price, direction, smc_data["fvgs"])
        scores["fvg"] = fvg_score
        if fvg_score > 0:
            reasons.append(f"FVG confluence: {fvg_score:.0%}")

        liq_score = self._score_liquidity(price, direction, smc_data["liquidity"])
        scores["liquidity_sweep"] = liq_score
        if liq_score > 0:
            reasons.append(f"Liquidity sweep: {liq_score:.0%}")

        trend_score = 1.0 if smc_data["bias"] == direction else 0.0
        scores["trend_alignment"] = trend_score
        if trend_score > 0:
            reasons.append("Aligned with HTF bias")

        session_score = self._score_session(hour)
        scores["session_time"] = session_score
        if session_score > 0:
            reasons.append(f"Active session: {session_score:.0%}")

        scores["volume_profile"] = 0.5

        total = sum(scores[k] * self.WEIGHTS[k] for k in self.WEIGHTS)

        entry, sl, tp = self._compute_levels(price, direction, smc_data)

        strength = SignalStrength.WEAK
        if total >= 0.95:
            strength = SignalStrength.ULTRA
        elif total >= 0.85:
            strength = SignalStrength.STRONG
        elif total >= 0.70:
            strength = SignalStrength.MODERATE

        return TradeSignal(
            direction=direction,
            entry=entry,
            stop_loss=sl,
            take_profit=tp,
            confluence_score=total,
            strength=strength,
            reasons=reasons,
        )

    def _score_order_blocks(self, price: float, direction: Direction, obs: list[OrderBlock]) -> float:
        if not obs:
            return 0.0
        relevant = [ob for ob in obs if ob.direction == direction]
        if not relevant:
            return 0.0

        for ob in relevant:
            if ob.low <= price <= ob.high:
                return 1.0
            dist = min(abs(price - ob.high), abs(price - ob.low))
            if dist / price < 0.001:
                return 0.7
        return 0.0

    def _score_fvgs(self, price: float, direction: Direction, fvgs: list[FairValueGap]) -> float:
        if not fvgs:
            return 0.0
        relevant = [fvg for fvg in fvgs if fvg.direction == direction]
        if not relevant:
            return 0.0

        for fvg in relevant:
            if fvg.low <= price <= fvg.high:
                return 1.0
            dist = min(abs(price - fvg.high), abs(price - fvg.low))
            if dist / price < 0.0005:
                return 0.5
        return 0.0

    def _score_liquidity(self, price: float, direction: Direction, levels: list[LiquiditySweep]) -> float:
        if not levels:
            return 0.0

        for liq in levels:
            dist = abs(price - liq.level) / price
            if dist < 0.0003 and liq.direction == direction:
                return 1.0
            elif dist < 0.001 and liq.direction == direction:
                return 0.5
        return 0.0

    def _score_session(self, hour: int) -> float:
        c = self.config.trading
        if c.session_london_start <= hour <= c.session_london_end:
            return 1.0
        if c.session_ny_start <= hour <= c.session_ny_end:
            return 1.0
        return 0.2

    def _compute_levels(self, price: float, direction: Direction, smc_data: dict) -> tuple:
        pip = 0.0001 if price < 10 else 0.01
        atr_estimate = pip * 10

        if direction == Direction.LONG:
            sl_candidates = [ob.low for ob in smc_data["order_blocks"] if ob.direction == Direction.LONG and ob.low < price]
            sl = min(sl_candidates) - (2 * pip) if sl_candidates else price - atr_estimate
            risk = price - sl
            tp = price + (risk * self.config.trading.take_profit_rr)
        else:
            sl_candidates = [ob.high for ob in smc_data["order_blocks"] if ob.direction == Direction.SHORT and ob.high > price]
            sl = max(sl_candidates) + (2 * pip) if sl_candidates else price + atr_estimate
            risk = sl - price
            tp = price - (risk * self.config.trading.take_profit_rr)

        return price, sl, tp


class NewsProtection:
    """Prevents trading around high-impact news events."""

    def __init__(self, buffer_minutes: int = 15):
        self.buffer_minutes = buffer_minutes
        self.blocked_windows: list[tuple[datetime, datetime]] = []

    def add_event(self, event_time: datetime) -> None:
        start = event_time - timedelta(minutes=self.buffer_minutes)
        end = event_time + timedelta(minutes=self.buffer_minutes)
        self.blocked_windows.append((start, end))

    def is_safe(self, now: Optional[datetime] = None) -> bool:
        now = now or datetime.now()
        return not any(start <= now <= end for start, end in self.blocked_windows)

    def clear_expired(self) -> None:
        now = datetime.now()
        self.blocked_windows = [(s, e) for s, e in self.blocked_windows if e > now]


class TrailStopManager:
    """Dynamic trailing stop based on ATR."""

    def __init__(self, atr_multiplier: float = 1.5):
        self.atr_multiplier = atr_multiplier

    def compute_trail(self, direction: Direction, current_price: float, atr: float, current_sl: float) -> float:
        trail_distance = atr * self.atr_multiplier

        if direction == Direction.LONG:
            new_sl = current_price - trail_distance
            return max(new_sl, current_sl)
        else:
            new_sl = current_price + trail_distance
            return min(new_sl, current_sl) if current_sl != 0 else new_sl


class MT5Connector:
    """MetaTrader 5 connection and order management.
    
    NOTE: MT5 Python API only works on Windows with MT5 installed.
    """

    def __init__(self, config):
        self.config = config
        self.mt5 = None
        self.connected = False

    def connect(self) -> bool:
        try:
            import MetaTrader5 as mt5
            self.mt5 = mt5

            if not mt5.initialize(path=self.config.mt5.path):
                logger.error(f"MT5 init failed: {mt5.last_error()}")
                return False

            if self.config.mt5.login:
                authorized = mt5.login(
                    login=self.config.mt5.login,
                    password=self.config.mt5.password,
                    server=self.config.mt5.server,
                )
                if not authorized:
                    logger.error(f"MT5 login failed: {mt5.last_error()}")
                    return False

            self.connected = True
            logger.info("MT5 connected successfully")
            return True

        except ImportError:
            logger.warning("MetaTrader5 package not available (requires Windows). Running in simulation mode.")
            return False

    def get_rates(self, symbol: str, timeframe_str: str, count: int) -> Optional[pd.DataFrame]:
        if not self.connected or self.mt5 is None:
            return self._generate_simulated_data(count)

        tf_map = {
            "M1": self.mt5.TIMEFRAME_M1,
            "M5": self.mt5.TIMEFRAME_M5,
            "M15": self.mt5.TIMEFRAME_M15,
            "H1": self.mt5.TIMEFRAME_H1,
            "H4": self.mt5.TIMEFRAME_H4,
            "D1": self.mt5.TIMEFRAME_D1,
        }
        tf = tf_map.get(timeframe_str, self.mt5.TIMEFRAME_M1)
        rates = self.mt5.copy_rates_from_pos(symbol, tf, 0, count)

        if rates is None or len(rates) == 0:
            return None

        df = pd.DataFrame(rates)
        df["time"] = pd.to_datetime(df["time"], unit="s")
        df.set_index("time", inplace=True)
        return df

    def get_current_price(self, symbol: str) -> Optional[tuple]:
        if not self.connected or self.mt5 is None:
            return None

        tick = self.mt5.symbol_info_tick(symbol)
        if tick is None:
            return None
        return tick.bid, tick.ask

    def place_order(self, signal: TradeSignal, lot_size: float, symbol: str) -> Optional[int]:
        if not self.connected or self.mt5 is None:
            logger.info(f"[SIM] Would place {signal.direction.value} {lot_size} lots @ {signal.entry}")
            return -1

        order_type = self.mt5.ORDER_TYPE_BUY if signal.direction == Direction.LONG else self.mt5.ORDER_TYPE_SELL
        price = self.mt5.symbol_info_tick(symbol)
        if price is None:
            return None

        fill_price = price.ask if signal.direction == Direction.LONG else price.bid

        request = {
            "action": self.mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": lot_size,
            "type": order_type,
            "price": fill_price,
            "sl": signal.stop_loss,
            "tp": signal.take_profit,
            "deviation": self.config.mt5.deviation,
            "magic": self.config.mt5.magic_number,
            "comment": f"JARVIS SMC {signal.strength.value}",
            "type_time": self.mt5.ORDER_TIME_GTC,
            "type_filling": self.mt5.ORDER_FILLING_IOC,
        }

        result = self.mt5.order_send(request)
        if result is None or result.retcode != self.mt5.TRADE_RETCODE_DONE:
            logger.error(f"Order failed: {result}")
            return None

        logger.info(f"Order placed: ticket={result.order}")
        return result.order

    def modify_sl(self, ticket: int, new_sl: float, symbol: str) -> bool:
        if not self.connected or self.mt5 is None:
            return False

        position = self.mt5.positions_get(ticket=ticket)
        if not position:
            return False

        request = {
            "action": self.mt5.TRADE_ACTION_SLTP,
            "position": ticket,
            "symbol": symbol,
            "sl": new_sl,
            "tp": position[0].tp,
        }
        result = self.mt5.order_send(request)
        return result is not None and result.retcode == self.mt5.TRADE_RETCODE_DONE

    def close_position(self, ticket: int, symbol: str) -> bool:
        if not self.connected or self.mt5 is None:
            return False

        position = self.mt5.positions_get(ticket=ticket)
        if not position:
            return False

        close_type = self.mt5.ORDER_TYPE_SELL if position[0].type == 0 else self.mt5.ORDER_TYPE_BUY
        price = self.mt5.symbol_info_tick(symbol)
        fill_price = price.bid if close_type == self.mt5.ORDER_TYPE_SELL else price.ask

        request = {
            "action": self.mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": position[0].volume,
            "type": close_type,
            "position": ticket,
            "price": fill_price,
            "deviation": self.config.mt5.deviation,
            "magic": self.config.mt5.magic_number,
            "comment": "JARVIS close",
        }
        result = self.mt5.order_send(request)
        return result is not None and result.retcode == self.mt5.TRADE_RETCODE_DONE

    def get_account_info(self) -> dict:
        if not self.connected or self.mt5 is None:
            return {"balance": 10.0, "equity": 10.0, "profit": 0.0, "margin_free": 10.0}

        info = self.mt5.account_info()
        return {
            "balance": info.balance,
            "equity": info.equity,
            "profit": info.profit,
            "margin_free": info.margin_free,
        }

    def shutdown(self) -> None:
        if self.mt5 is not None:
            self.mt5.shutdown()
            self.connected = False

    @staticmethod
    def _generate_simulated_data(count: int) -> pd.DataFrame:
        np.random.seed(int(time.time()) % 10000)
        base = 1.0850
        dates = pd.date_range(end=datetime.now(), periods=count, freq="1min")
        prices = [base]
        for _ in range(count - 1):
            prices.append(prices[-1] + np.random.normal(0, 0.0002))

        df = pd.DataFrame({
            "open": prices,
            "high": [p + abs(np.random.normal(0, 0.0003)) for p in prices],
            "low": [p - abs(np.random.normal(0, 0.0003)) for p in prices],
            "close": [p + np.random.normal(0, 0.0001) for p in prices],
            "tick_volume": np.random.randint(50, 500, count),
        }, index=dates)
        return df


class RiskManager:
    """Position sizing and risk controls."""

    def __init__(self, config):
        self.config = config
        self.daily_pnl: float = 0.0
        self.trades_today: int = 0
        self.daily_reset_date: Optional[datetime] = None

    def check_daily_reset(self) -> None:
        today = datetime.now().date()
        if self.daily_reset_date != today:
            self.daily_pnl = 0.0
            self.trades_today = 0
            self.daily_reset_date = today

    def is_trading_allowed(self, balance: float) -> tuple[bool, str]:
        self.check_daily_reset()

        max_loss = balance * (self.config.trading.max_daily_loss_pct / 100)
        if self.daily_pnl <= -max_loss:
            return False, f"Daily loss limit reached: {self.daily_pnl:.2f}"

        return True, "OK"

    def calculate_lot_size(self, balance: float, sl_pips: float) -> float:
        risk_amount = balance * (self.config.trading.risk_per_trade_pct / 100)
        if sl_pips <= 0:
            return 0.01

        pip_value = 10.0
        lot_size = risk_amount / (sl_pips * pip_value)
        lot_size = max(0.01, min(lot_size, 1.0))
        return round(lot_size, 2)

    def record_trade_result(self, pnl: float) -> None:
        self.daily_pnl += pnl
        self.trades_today += 1


class TradingUltima:
    """Main trading orchestrator combining all SMC components."""

    def __init__(self, config):
        self.config = config
        self.smc = SMCAnalyzer()
        self.confluence = ConfluenceEngine(config)
        self.news_guard = NewsProtection(config.trading.news_protection_minutes)
        self.trail_mgr = TrailStopManager(config.trading.trail_stop_atr_mult)
        self.risk_mgr = RiskManager(config)
        self.mt5 = MT5Connector(config)
        self.active_trades: list[TradeRecord] = []
        self.trade_history: list[TradeRecord] = []
        self.running = False
        self._last_signal: Optional[TradeSignal] = None
        self._equity_curve: list[float] = []

    def initialize(self) -> bool:
        connected = self.mt5.connect()
        if not connected:
            logger.warning("Running in SIMULATION mode - MT5 not available")
        return True

    def scan_for_signals(self) -> Optional[TradeSignal]:
        df = self.mt5.get_rates(self.config.mt5.symbol, self.config.mt5.timeframe, 200)
        if df is None or len(df) < 50:
            return None

        smc_data = self.smc.analyze(df)
        if smc_data["bias"] is None:
            return None

        current_price = df["close"].iloc[-1]
        hour = datetime.now().hour

        signal = self.confluence.score(current_price, smc_data["bias"], smc_data, hour)

        if signal.confluence_score >= self.config.trading.min_confluence_score:
            self._last_signal = signal
            logger.info(
                f"Signal: {signal.direction.value} | Score: {signal.confluence_score:.2%} | "
                f"Entry: {signal.entry:.5f} | SL: {signal.stop_loss:.5f} | TP: {signal.take_profit:.5f} | "
                f"RR: {signal.risk_reward:.1f}"
            )
            return signal

        return None

    def execute_signal(self, signal: TradeSignal) -> Optional[TradeRecord]:
        if not self.news_guard.is_safe():
            logger.info("Trade blocked: news protection active")
            return None

        if len(self.active_trades) >= self.config.trading.max_concurrent_trades:
            logger.info("Trade blocked: max concurrent trades reached")
            return None

        account = self.mt5.get_account_info()
        allowed, reason = self.risk_mgr.is_trading_allowed(account["balance"])
        if not allowed:
            logger.warning(f"Trade blocked: {reason}")
            return None

        sl_pips = abs(signal.entry - signal.stop_loss) / 0.0001
        lot_size = self.risk_mgr.calculate_lot_size(account["balance"], sl_pips)

        ticket = self.mt5.place_order(signal, lot_size, self.config.mt5.symbol)
        if ticket is None:
            return None

        trade = TradeRecord(
            ticket=ticket,
            direction=signal.direction,
            entry_price=signal.entry,
            stop_loss=signal.stop_loss,
            take_profit=signal.take_profit,
            lot_size=lot_size,
            open_time=datetime.now(),
        )
        self.active_trades.append(trade)
        logger.info(f"Trade opened: #{ticket} {signal.direction.value} {lot_size} lots")
        return trade

    def manage_positions(self) -> None:
        df = self.mt5.get_rates(self.config.mt5.symbol, self.config.mt5.timeframe, 50)
        if df is None:
            return

        atr = self._calculate_atr(df)

        for trade in self.active_trades[:]:
            current_price = df["close"].iloc[-1]

            new_sl = self.trail_mgr.compute_trail(
                trade.direction, current_price, atr, trade.stop_loss
            )
            if new_sl != trade.stop_loss:
                if self.mt5.modify_sl(trade.ticket, new_sl, self.config.mt5.symbol):
                    trade.stop_loss = new_sl
                    logger.info(f"Trail stop updated: #{trade.ticket} SL={new_sl:.5f}")

    def update_equity_curve(self) -> None:
        account = self.mt5.get_account_info()
        self._equity_curve.append(account["equity"])

    @property
    def equity_curve(self) -> list[float]:
        return self._equity_curve

    @property
    def last_signal(self) -> Optional[TradeSignal]:
        return self._last_signal

    def get_status(self) -> dict:
        account = self.mt5.get_account_info()
        return {
            "connected": self.mt5.connected,
            "balance": account["balance"],
            "equity": account["equity"],
            "profit": account["profit"],
            "active_trades": len(self.active_trades),
            "total_trades": len(self.trade_history),
            "daily_pnl": self.risk_mgr.daily_pnl,
            "last_signal": self._last_signal,
            "running": self.running,
        }

    def run_cycle(self) -> Optional[TradeSignal]:
        self.news_guard.clear_expired()
        self.manage_positions()
        self.update_equity_curve()

        signal = self.scan_for_signals()
        if signal:
            self.execute_signal(signal)
        return signal

    @staticmethod
    def _calculate_atr(df: pd.DataFrame, period: int = 14) -> float:
        highs = df["high"].values
        lows = df["low"].values
        closes = df["close"].values

        trs = []
        for i in range(1, len(df)):
            tr = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i - 1]),
                abs(lows[i] - closes[i - 1]),
            )
            trs.append(tr)

        if not trs:
            return 0.0
        return np.mean(trs[-period:])
