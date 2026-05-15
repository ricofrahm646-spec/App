"""
Tick-Level Backtesting Engine
==============================

High-fidelity tick-by-tick simulation with realistic spread, slippage,
and partial fill modeling for precise strategy evaluation.
"""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


class OrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderSide(Enum):
    BUY = "buy"
    SELL = "sell"


class OrderStatus(Enum):
    PENDING = "pending"
    PARTIAL = "partial"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


@dataclass
class Tick:
    """A single market tick."""

    timestamp: float
    bid: float
    ask: float
    last: float
    volume: float = 0.0
    flags: int = 0

    @property
    def mid(self) -> float:
        return (self.bid + self.ask) / 2.0

    @property
    def spread(self) -> float:
        return self.ask - self.bid


@dataclass
class Order:
    """A pending or executed order."""

    order_id: int
    side: OrderSide
    order_type: OrderType
    price: float
    size: float
    filled_size: float = 0.0
    avg_fill_price: float = 0.0
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    status: OrderStatus = OrderStatus.PENDING
    created_at: float = 0.0
    filled_at: float = 0.0
    slippage: float = 0.0
    commission: float = 0.0
    fills: List[Dict[str, float]] = field(default_factory=list)
    tag: str = ""

    @property
    def remaining_size(self) -> float:
        return self.size - self.filled_size


@dataclass
class Position:
    """Current position state."""

    size: float = 0.0
    avg_entry_price: float = 0.0
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    side: Optional[OrderSide] = None

    @property
    def is_flat(self) -> bool:
        return abs(self.size) < 1e-10


@dataclass
class TickEngineConfig:
    """Configuration for the tick-level backtesting engine."""

    initial_capital: float = 10000.0
    commission_per_lot: float = 7.0
    min_commission: float = 1.0
    base_spread: float = 0.00015  # 1.5 pips for forex
    spread_volatility_factor: float = 0.5
    base_slippage: float = 0.00005
    slippage_volatility_factor: float = 1.0
    max_slippage: float = 0.001
    partial_fill_probability: float = 0.1
    min_fill_ratio: float = 0.3
    max_pending_orders: int = 50
    latency_ms: float = 50.0
    latency_std_ms: float = 20.0
    seed: int = 42


@dataclass
class TickTradeRecord:
    """Detailed record of a completed tick-level trade."""

    trade_id: int
    entry_order_id: int
    exit_order_id: int
    side: str
    entry_price: float
    exit_price: float
    size: float
    gross_pnl: float
    commission: float
    slippage: float
    net_pnl: float
    entry_time: float
    exit_time: float
    duration_ticks: int
    entry_spread: float
    exit_spread: float
    n_fills: int


@dataclass
class TickBacktestResult:
    """Complete tick-level backtest result."""

    trades: List[TickTradeRecord]
    equity_curve: List[float]
    timestamps: List[float]
    n_ticks_processed: int
    metrics: Dict[str, float]
    config: TickEngineConfig
    order_history: List[Order]


class SpreadSimulator:
    """Simulate realistic bid-ask spreads based on market conditions."""

    def __init__(
        self,
        base_spread: float = 0.00015,
        volatility_factor: float = 0.5,
        seed: int = 42,
    ):
        self.base_spread = base_spread
        self.volatility_factor = volatility_factor
        self.rng = np.random.RandomState(seed)
        self._recent_returns: List[float] = []
        self._max_history = 100

    def get_spread(self, mid_price: float, tick: Optional[Tick] = None) -> float:
        """
        Compute the current spread based on recent volatility.

        Spread widens during high-volatility periods and narrows during
        calm markets.
        """
        if tick and self._recent_returns:
            recent_vol = np.std(self._recent_returns[-20:]) if len(self._recent_returns) >= 20 else 0.0
            avg_vol = np.std(self._recent_returns) if self._recent_returns else 0.0

            vol_ratio = recent_vol / (avg_vol + 1e-10) if avg_vol > 0 else 1.0
            vol_multiplier = 1.0 + (vol_ratio - 1.0) * self.volatility_factor
            vol_multiplier = max(0.5, min(3.0, vol_multiplier))
        else:
            vol_multiplier = 1.0

        noise = self.rng.lognormal(0, 0.1)
        spread = self.base_spread * vol_multiplier * noise * mid_price

        return max(spread, self.base_spread * mid_price * 0.5)

    def update(self, ret: float) -> None:
        """Update the return history for volatility calculation."""
        self._recent_returns.append(ret)
        if len(self._recent_returns) > self._max_history:
            self._recent_returns.pop(0)


class SlippageModel:
    """Model realistic slippage based on order size and market volatility."""

    def __init__(
        self,
        base_slippage: float = 0.00005,
        volatility_factor: float = 1.0,
        max_slippage: float = 0.001,
        seed: int = 42,
    ):
        self.base_slippage = base_slippage
        self.volatility_factor = volatility_factor
        self.max_slippage = max_slippage
        self.rng = np.random.RandomState(seed)
        self._recent_vol: float = 0.0

    def compute_slippage(
        self,
        price: float,
        order_size: float,
        side: OrderSide,
        spread: float,
    ) -> float:
        """
        Compute execution slippage for an order.

        Slippage increases with:
        - Order size (market impact)
        - Market volatility
        - Wider spreads
        """
        size_impact = np.log1p(order_size) * 0.0001

        vol_impact = self._recent_vol * self.volatility_factor

        spread_impact = spread / (price + 1e-10) * 0.5

        base = self.base_slippage + size_impact + vol_impact + spread_impact
        noise = abs(self.rng.normal(0, base * 0.5))
        slippage = (base + noise) * price

        return min(slippage, self.max_slippage * price)

    def update_volatility(self, vol: float) -> None:
        """Update the current volatility estimate."""
        self._recent_vol = vol


class PartialFillSimulator:
    """Simulate partial order fills based on available liquidity."""

    def __init__(
        self,
        partial_fill_prob: float = 0.1,
        min_fill_ratio: float = 0.3,
        seed: int = 42,
    ):
        self.partial_fill_prob = partial_fill_prob
        self.min_fill_ratio = min_fill_ratio
        self.rng = np.random.RandomState(seed)

    def simulate_fill(
        self,
        order: Order,
        available_price: float,
    ) -> List[Dict[str, float]]:
        """
        Simulate the fill of an order, possibly with partial fills.

        Returns a list of fill records [{price, size, timestamp}].
        """
        remaining = order.remaining_size

        if remaining <= 0:
            return []

        if self.rng.random() < self.partial_fill_prob and order.order_type == OrderType.MARKET:
            fill_ratio = self.rng.uniform(self.min_fill_ratio, 1.0)
            fill_size = remaining * fill_ratio
        else:
            fill_size = remaining

        fills = [{
            "price": available_price,
            "size": fill_size,
        }]

        return fills


class TickEngine:
    """
    Tick-by-tick backtesting engine with realistic market microstructure.

    Processes individual ticks, manages orders with spread/slippage
    simulation, and produces detailed execution records.
    """

    def __init__(self, config: Optional[TickEngineConfig] = None):
        self.config = config or TickEngineConfig()
        self.spread_sim = SpreadSimulator(
            base_spread=self.config.base_spread,
            volatility_factor=self.config.spread_volatility_factor,
            seed=self.config.seed,
        )
        self.slippage_model = SlippageModel(
            base_slippage=self.config.base_slippage,
            volatility_factor=self.config.slippage_volatility_factor,
            max_slippage=self.config.max_slippage,
            seed=self.config.seed + 1,
        )
        self.fill_sim = PartialFillSimulator(
            partial_fill_prob=self.config.partial_fill_probability,
            min_fill_ratio=self.config.min_fill_ratio,
            seed=self.config.seed + 2,
        )

        self._reset()

    def _reset(self) -> None:
        self.cash = self.config.initial_capital
        self.position = Position()
        self.pending_orders: List[Order] = []
        self.order_history: List[Order] = []
        self.trade_records: List[TickTradeRecord] = []
        self.equity_curve: List[float] = []
        self.timestamps: List[float] = []
        self._order_counter = 0
        self._trade_counter = 0
        self._prev_price: Optional[float] = None
        self._tick_count = 0
        self._entry_tick = 0
        self._entry_spread = 0.0

    def run(
        self,
        ticks: List[Tick],
        strategy_fn: Callable[
            ["TickEngine", Tick, Position], Optional[Tuple[OrderSide, float]]
        ],
    ) -> TickBacktestResult:
        """
        Run a tick-by-tick backtest.

        Args:
            ticks: List of Tick objects in chronological order.
            strategy_fn: Callable(engine, tick, position) -> Optional[(side, size)]
                         Returns None for no action, or (side, size) to place
                         a market order.

        Returns:
            TickBacktestResult with detailed execution records.
        """
        self._reset()

        for tick in ticks:
            self._process_tick(tick, strategy_fn)

        if not self.position.is_flat:
            last_tick = ticks[-1] if ticks else None
            if last_tick:
                side = OrderSide.SELL if self.position.size > 0 else OrderSide.BUY
                self._place_market_order(side, abs(self.position.size))
                self._process_pending_orders(last_tick)

        metrics = self._compute_metrics()

        return TickBacktestResult(
            trades=self.trade_records,
            equity_curve=self.equity_curve,
            timestamps=self.timestamps,
            n_ticks_processed=self._tick_count,
            metrics=metrics,
            config=self.config,
            order_history=self.order_history,
        )

    def run_from_ohlcv(
        self,
        open_prices: np.ndarray,
        high_prices: np.ndarray,
        low_prices: np.ndarray,
        close_prices: np.ndarray,
        volumes: np.ndarray,
        strategy_fn: Callable[
            ["TickEngine", Tick, Position], Optional[Tuple[OrderSide, float]]
        ],
        ticks_per_bar: int = 4,
    ) -> TickBacktestResult:
        """
        Synthesize ticks from OHLCV data and run the backtest.

        Generates `ticks_per_bar` ticks per bar following the O→H→L→C
        or O→L→H→C path based on the bar direction.
        """
        ticks: List[Tick] = []
        n = len(close_prices)

        for i in range(n):
            o, h, l, c = open_prices[i], high_prices[i], low_prices[i], close_prices[i]
            v = volumes[i] if volumes is not None else 0.0
            bar_ticks = self._synthesize_bar_ticks(
                i, o, h, l, c, v, ticks_per_bar
            )
            ticks.extend(bar_ticks)

        return self.run(ticks, strategy_fn)

    def place_order(
        self,
        side: OrderSide,
        size: float,
        order_type: OrderType = OrderType.MARKET,
        price: float = 0.0,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        tag: str = "",
    ) -> Order:
        """Place a new order."""
        self._order_counter += 1
        order = Order(
            order_id=self._order_counter,
            side=side,
            order_type=order_type,
            price=price,
            size=size,
            stop_loss=stop_loss,
            take_profit=take_profit,
            tag=tag,
        )
        self.pending_orders.append(order)
        return order

    def cancel_order(self, order_id: int) -> bool:
        """Cancel a pending order by ID."""
        for i, order in enumerate(self.pending_orders):
            if order.order_id == order_id and order.status == OrderStatus.PENDING:
                order.status = OrderStatus.CANCELLED
                self.order_history.append(order)
                self.pending_orders.pop(i)
                return True
        return False

    def cancel_all_orders(self) -> int:
        """Cancel all pending orders."""
        count = 0
        for order in self.pending_orders:
            if order.status in (OrderStatus.PENDING, OrderStatus.PARTIAL):
                order.status = OrderStatus.CANCELLED
                self.order_history.append(order)
                count += 1
        self.pending_orders.clear()
        return count

    def _place_market_order(self, side: OrderSide, size: float) -> Order:
        return self.place_order(side, size, OrderType.MARKET)

    def _process_tick(
        self,
        tick: Tick,
        strategy_fn: Callable,
    ) -> None:
        self._tick_count += 1

        if self._prev_price is not None:
            ret = (tick.mid - self._prev_price) / (self._prev_price + 1e-10)
            self.spread_sim.update(ret)

        if not self.position.is_flat:
            if self.position.size > 0:
                self.position.unrealized_pnl = (
                    (tick.bid - self.position.avg_entry_price) * self.position.size
                )
            else:
                self.position.unrealized_pnl = (
                    (self.position.avg_entry_price - tick.ask) * abs(self.position.size)
                )

        self._check_sl_tp(tick)
        self._process_pending_orders(tick)

        action = strategy_fn(self, tick, self.position)
        if action is not None:
            side, size = action
            self._place_market_order(side, size)
            self._process_pending_orders(tick)

        equity = self.cash + self.position.unrealized_pnl
        if not self.position.is_flat:
            equity += self.position.avg_entry_price * abs(self.position.size)
        self.equity_curve.append(equity)
        self.timestamps.append(tick.timestamp)

        self._prev_price = tick.mid

    def _process_pending_orders(self, tick: Tick) -> None:
        filled_orders: List[int] = []

        for i, order in enumerate(self.pending_orders):
            if order.status in (OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.REJECTED):
                filled_orders.append(i)
                continue

            should_fill = False
            fill_price = 0.0

            if order.order_type == OrderType.MARKET:
                should_fill = True
                fill_price = tick.ask if order.side == OrderSide.BUY else tick.bid
            elif order.order_type == OrderType.LIMIT:
                if order.side == OrderSide.BUY and tick.ask <= order.price:
                    should_fill = True
                    fill_price = min(tick.ask, order.price)
                elif order.side == OrderSide.SELL and tick.bid >= order.price:
                    should_fill = True
                    fill_price = max(tick.bid, order.price)
            elif order.order_type == OrderType.STOP:
                if order.side == OrderSide.BUY and tick.ask >= order.price:
                    should_fill = True
                    fill_price = tick.ask
                elif order.side == OrderSide.SELL and tick.bid <= order.price:
                    should_fill = True
                    fill_price = tick.bid

            if should_fill:
                self._execute_fill(order, fill_price, tick)
                if order.status == OrderStatus.FILLED:
                    filled_orders.append(i)

        for i in sorted(filled_orders, reverse=True):
            if i < len(self.pending_orders):
                self.order_history.append(self.pending_orders.pop(i))

    def _execute_fill(self, order: Order, raw_price: float, tick: Tick) -> None:
        spread = tick.spread
        slippage = self.slippage_model.compute_slippage(
            raw_price, order.remaining_size, order.side, spread
        )

        if order.side == OrderSide.BUY:
            adjusted_price = raw_price + slippage
        else:
            adjusted_price = raw_price - slippage

        fills = self.fill_sim.simulate_fill(order, adjusted_price)

        for fill in fills:
            fill_price = fill["price"]
            fill_size = fill["size"]

            commission = max(
                fill_size * self.config.commission_per_lot,
                self.config.min_commission,
            )

            was_flat = self.position.is_flat
            prev_side = self.position.side

            if order.side == OrderSide.BUY:
                if self.position.size < 0:
                    close_size = min(fill_size, abs(self.position.size))
                    pnl = (self.position.avg_entry_price - fill_price) * close_size - commission
                    self.position.realized_pnl += pnl
                    self.cash += pnl
                    self.position.size += close_size
                    remaining = fill_size - close_size

                    if remaining > 0:
                        self._record_trade(order, fill_price, close_size, pnl, tick, "short")
                        self.position.avg_entry_price = fill_price
                        self.position.size = remaining
                        self.position.side = OrderSide.BUY
                        self._entry_tick = self._tick_count
                        self._entry_spread = spread
                    else:
                        self._record_trade(order, fill_price, close_size, pnl, tick, "short")
                        if self.position.is_flat:
                            self.position.side = None
                            self.position.avg_entry_price = 0.0
                else:
                    if self.position.is_flat:
                        self.position.avg_entry_price = fill_price
                        self.position.size = fill_size
                        self.position.side = OrderSide.BUY
                        self._entry_tick = self._tick_count
                        self._entry_spread = spread
                        self.cash -= commission
                    else:
                        total_cost = (
                            self.position.avg_entry_price * self.position.size
                            + fill_price * fill_size
                        )
                        self.position.size += fill_size
                        self.position.avg_entry_price = total_cost / self.position.size
                        self.cash -= commission
            else:
                if self.position.size > 0:
                    close_size = min(fill_size, self.position.size)
                    pnl = (fill_price - self.position.avg_entry_price) * close_size - commission
                    self.position.realized_pnl += pnl
                    self.cash += pnl
                    self.position.size -= close_size
                    remaining = fill_size - close_size

                    if remaining > 0:
                        self._record_trade(order, fill_price, close_size, pnl, tick, "long")
                        self.position.avg_entry_price = fill_price
                        self.position.size = -remaining
                        self.position.side = OrderSide.SELL
                        self._entry_tick = self._tick_count
                        self._entry_spread = spread
                    else:
                        self._record_trade(order, fill_price, close_size, pnl, tick, "long")
                        if self.position.is_flat:
                            self.position.side = None
                            self.position.avg_entry_price = 0.0
                else:
                    if self.position.is_flat:
                        self.position.avg_entry_price = fill_price
                        self.position.size = -fill_size
                        self.position.side = OrderSide.SELL
                        self._entry_tick = self._tick_count
                        self._entry_spread = spread
                        self.cash -= commission
                    else:
                        total_cost = (
                            self.position.avg_entry_price * abs(self.position.size)
                            + fill_price * fill_size
                        )
                        self.position.size -= fill_size
                        self.position.avg_entry_price = total_cost / abs(self.position.size)
                        self.cash -= commission

            order.filled_size += fill_size
            if order.filled_size > 0:
                order.avg_fill_price = (
                    (order.avg_fill_price * (order.filled_size - fill_size) + fill_price * fill_size)
                    / order.filled_size
                )
            order.fills.append(fill)
            order.slippage += slippage * fill_size
            order.commission += commission

        if order.remaining_size <= 1e-10:
            order.status = OrderStatus.FILLED
            order.filled_at = tick.timestamp
        else:
            order.status = OrderStatus.PARTIAL

    def _record_trade(
        self, exit_order: Order, exit_price: float, size: float,
        pnl: float, tick: Tick, side: str,
    ) -> None:
        self._trade_counter += 1
        self.trade_records.append(TickTradeRecord(
            trade_id=self._trade_counter,
            entry_order_id=0,
            exit_order_id=exit_order.order_id,
            side=side,
            entry_price=self.position.avg_entry_price,
            exit_price=exit_price,
            size=size,
            gross_pnl=pnl + exit_order.commission,
            commission=exit_order.commission,
            slippage=exit_order.slippage,
            net_pnl=pnl,
            entry_time=0.0,
            exit_time=tick.timestamp,
            duration_ticks=self._tick_count - self._entry_tick,
            entry_spread=self._entry_spread,
            exit_spread=tick.spread,
            n_fills=len(exit_order.fills),
        ))

    def _check_sl_tp(self, tick: Tick) -> None:
        """Check stop-loss and take-profit for the current position."""
        if self.position.is_flat:
            return

        for order in list(self.pending_orders):
            if order.status != OrderStatus.PENDING:
                continue

            if order.stop_loss is not None:
                if self.position.size > 0 and tick.bid <= order.stop_loss:
                    sl_order = self._place_market_order(OrderSide.SELL, abs(self.position.size))
                    sl_order.tag = "stop_loss"
                    break
                elif self.position.size < 0 and tick.ask >= order.stop_loss:
                    sl_order = self._place_market_order(OrderSide.BUY, abs(self.position.size))
                    sl_order.tag = "stop_loss"
                    break

            if order.take_profit is not None:
                if self.position.size > 0 and tick.bid >= order.take_profit:
                    tp_order = self._place_market_order(OrderSide.SELL, abs(self.position.size))
                    tp_order.tag = "take_profit"
                    break
                elif self.position.size < 0 and tick.ask <= order.take_profit:
                    tp_order = self._place_market_order(OrderSide.BUY, abs(self.position.size))
                    tp_order.tag = "take_profit"
                    break

    def _synthesize_bar_ticks(
        self, bar_idx: int, o: float, h: float, l: float, c: float,
        v: float, n_ticks: int,
    ) -> List[Tick]:
        """Generate synthetic ticks from a single OHLCV bar."""
        ticks = []
        is_bullish = c >= o

        if is_bullish:
            path = [o, h, l, c]
        else:
            path = [o, l, h, c]

        if n_ticks <= 4:
            prices = path[:n_ticks]
        else:
            prices = np.interp(
                np.linspace(0, len(path) - 1, n_ticks),
                np.arange(len(path)),
                path,
            )

        vol_per_tick = v / n_ticks if n_ticks > 0 else 0

        for j, price in enumerate(prices):
            spread = self.spread_sim.get_spread(price)
            half_spread = spread / 2
            ticks.append(Tick(
                timestamp=bar_idx + j / n_ticks,
                bid=price - half_spread,
                ask=price + half_spread,
                last=price,
                volume=vol_per_tick,
            ))

        return ticks

    def _compute_metrics(self) -> Dict[str, float]:
        trades = self.trade_records
        equity = np.array(self.equity_curve) if self.equity_curve else np.array([self.config.initial_capital])

        n_trades = len(trades)
        if n_trades == 0:
            return {
                "total_trades": 0, "final_equity": float(equity[-1]),
                "total_return": 0.0, "sharpe_ratio": 0.0,
            }

        wins = [t for t in trades if t.net_pnl > 0]
        losses = [t for t in trades if t.net_pnl <= 0]

        total_pnl = sum(t.net_pnl for t in trades)
        total_commission = sum(t.commission for t in trades)
        total_slippage = sum(t.slippage for t in trades)

        returns = np.diff(equity) / (equity[:-1] + 1e-10) if len(equity) > 1 else np.array([0.0])
        sharpe = float(np.mean(returns) / (np.std(returns) + 1e-10) * np.sqrt(252 * 24 * 60))

        peak = np.maximum.accumulate(equity)
        drawdown = (peak - equity) / (peak + 1e-10)
        max_dd = float(np.max(drawdown))

        return {
            "total_trades": n_trades,
            "winning_trades": len(wins),
            "losing_trades": len(losses),
            "win_rate": len(wins) / n_trades,
            "total_pnl": total_pnl,
            "total_commission": total_commission,
            "total_slippage": total_slippage,
            "avg_trade_pnl": total_pnl / n_trades,
            "avg_win": np.mean([t.net_pnl for t in wins]) if wins else 0.0,
            "avg_loss": np.mean([abs(t.net_pnl) for t in losses]) if losses else 0.0,
            "profit_factor": (
                sum(t.net_pnl for t in wins) / (sum(abs(t.net_pnl) for t in losses) + 1e-10)
            ),
            "final_equity": float(equity[-1]),
            "total_return": (equity[-1] - equity[0]) / (equity[0] + 1e-10),
            "sharpe_ratio": sharpe,
            "max_drawdown": max_dd,
            "avg_spread": np.mean([t.entry_spread for t in trades]) if trades else 0.0,
            "avg_fills_per_trade": np.mean([t.n_fills for t in trades]) if trades else 0.0,
            "avg_duration_ticks": np.mean([t.duration_ticks for t in trades]) if trades else 0.0,
        }
