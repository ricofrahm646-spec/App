"""
trader_ultimate.py
==================
J.A.R.V.I.S. V300 - Trading Ultima

Aggressive M1 SMC scalper plugged into the MetaTrader 5 terminal.
Implements:

    * Smart Money Concepts (Orderblocks, FVG, Liquidity Sweeps, BOS/CHoCH,
      Premium/Discount) via :pymod:`core.smc`.
    * HTF bias filter (M15 EMA 50/200).
    * 90%+ confluence gate before any order is placed.
    * ATR-based stop loss and Risk-multiplied take profit.
    * Server-side trailing stop once trade is +1R in profit.
    * News-blackout window pulled from a JSON file written by ghost_security.
    * Daily drawdown circuit breaker.
    * One-position-at-a-time discipline; magic number isolated.
    * 10 EUR -> 100 EUR campaign tracker writes equity to logs/equity.csv.

Run standalone:
    python trader_ultimate.py
"""
from __future__ import annotations

import json
import math
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

from config import RESEARCH_DIR, STATE_DIR, TRADING
from core import bus
from core.smc import Confluence, analyze, htf_bias, score_confluence

try:
    import MetaTrader5 as mt5  # type: ignore
    MT5_AVAILABLE = True
except Exception:  # pragma: no cover - only available on Windows w/ MT5 terminal
    mt5 = None  # type: ignore
    MT5_AVAILABLE = False


# ---------------------------------------------------------------------------
# News protection
# ---------------------------------------------------------------------------
NEWS_FILE = RESEARCH_DIR / "news.json"


def is_news_blackout(symbol: str, blackout_minutes: int) -> bool:
    """Check :file:`data/research/news.json` produced by ghost_security."""
    if not NEWS_FILE.exists():
        return False
    try:
        data = json.loads(NEWS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return False
    now = datetime.now(timezone.utc)
    window = timedelta(minutes=blackout_minutes)
    for item in data.get("events", []):
        if item.get("impact", "").lower() != "high":
            continue
        # Only block trades when the news currency matches the symbol
        ccy = (item.get("currency") or "").upper()
        if ccy and ccy not in symbol.upper():
            continue
        try:
            t = datetime.fromisoformat(item["time"].replace("Z", "+00:00"))
        except Exception:
            continue
        if abs((t - now).total_seconds()) <= window.total_seconds():
            return True
    return False


# ---------------------------------------------------------------------------
# Risk
# ---------------------------------------------------------------------------
@dataclass
class RiskPlan:
    lots: float
    sl: float
    tp: float
    risk_money: float


def _round_lots(symbol_info, lots: float) -> float:
    step = float(symbol_info.volume_step or 0.01)
    min_l = float(symbol_info.volume_min or 0.01)
    max_l = float(symbol_info.volume_max or 100.0)
    lots = max(min_l, min(max_l, lots))
    lots = math.floor(lots / step) * step
    return round(lots, 2)


def build_risk_plan(symbol: str, direction: str, price: float, atr: float, account_equity: float) -> Optional[RiskPlan]:
    if not MT5_AVAILABLE:
        return None
    info = mt5.symbol_info(symbol)
    if info is None:
        return None
    point = info.point
    sl_distance = max(atr * TRADING.sl_atr_mult, info.trade_stops_level * point * 1.5)
    if sl_distance <= 0:
        return None
    if direction == "BUY":
        sl = price - sl_distance
        tp = price + sl_distance * TRADING.tp_rr
    else:
        sl = price + sl_distance
        tp = price - sl_distance * TRADING.tp_rr

    tick_value = info.trade_tick_value or 1.0
    tick_size = info.trade_tick_size or point
    if tick_size <= 0:
        return None
    # Money risked per 1.0 lot for the given SL distance:
    risk_per_lot = (sl_distance / tick_size) * tick_value
    if risk_per_lot <= 0:
        return None

    risk_money = account_equity * TRADING.risk_per_trade
    lots = _round_lots(info, risk_money / risk_per_lot)
    if lots <= 0:
        return None
    return RiskPlan(lots=lots, sl=sl, tp=tp, risk_money=risk_money)


# ---------------------------------------------------------------------------
# MT5 helpers
# ---------------------------------------------------------------------------
TF_MAP_LAZY = {
    1: "TIMEFRAME_M1",
    5: "TIMEFRAME_M5",
    15: "TIMEFRAME_M15",
    30: "TIMEFRAME_M30",
    60: "TIMEFRAME_H1",
    240: "TIMEFRAME_H4",
    1440: "TIMEFRAME_D1",
}


def _tf(minutes: int):
    if not MT5_AVAILABLE:
        return None
    name = TF_MAP_LAZY.get(minutes, "TIMEFRAME_M1")
    return getattr(mt5, name)


def fetch_rates(symbol: str, minutes: int, count: int) -> Optional[pd.DataFrame]:
    if not MT5_AVAILABLE:
        return None
    if not mt5.symbol_select(symbol, True):
        return None
    rates = mt5.copy_rates_from_pos(symbol, _tf(minutes), 0, count)
    if rates is None or len(rates) == 0:
        return None
    df = pd.DataFrame(rates)
    df.rename(columns={"tick_volume": "volume"}, inplace=True)
    df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)
    return df


def current_position(symbol: str):
    if not MT5_AVAILABLE:
        return None
    positions = mt5.positions_get(symbol=symbol)
    if not positions:
        return None
    for p in positions:
        if p.magic == TRADING.magic_number:
            return p
    return None


def send_order(symbol: str, direction: str, lots: float, sl: float, tp: float) -> bool:
    if not MT5_AVAILABLE:
        return False
    tick = mt5.symbol_info_tick(symbol)
    if not tick:
        return False
    price = tick.ask if direction == "BUY" else tick.bid
    order_type = mt5.ORDER_TYPE_BUY if direction == "BUY" else mt5.ORDER_TYPE_SELL
    req = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": lots,
        "type": order_type,
        "price": price,
        "sl": sl,
        "tp": tp,
        "deviation": TRADING.slippage_points,
        "magic": TRADING.magic_number,
        "comment": TRADING.comment,
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    result = mt5.order_send(req)
    ok = result is not None and result.retcode == mt5.TRADE_RETCODE_DONE
    bus.log_trade({
        "action": "OPEN",
        "symbol": symbol,
        "direction": direction,
        "lots": lots,
        "price": price,
        "sl": sl,
        "tp": tp,
        "ok": ok,
        "retcode": getattr(result, "retcode", None),
        "comment": getattr(result, "comment", ""),
    })
    return ok


def modify_sl(symbol: str, position, new_sl: float) -> bool:
    if not MT5_AVAILABLE:
        return False
    req = {
        "action": mt5.TRADE_ACTION_SLTP,
        "symbol": symbol,
        "position": position.ticket,
        "sl": new_sl,
        "tp": position.tp,
        "magic": TRADING.magic_number,
    }
    res = mt5.order_send(req)
    ok = res is not None and res.retcode == mt5.TRADE_RETCODE_DONE
    if ok:
        bus.log_trade({"action": "TRAIL", "symbol": symbol, "sl": new_sl, "ticket": position.ticket})
    return ok


def close_position(symbol: str, position) -> bool:
    if not MT5_AVAILABLE:
        return False
    tick = mt5.symbol_info_tick(symbol)
    if not tick:
        return False
    is_buy = position.type == mt5.POSITION_TYPE_BUY
    req = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": position.volume,
        "type": mt5.ORDER_TYPE_SELL if is_buy else mt5.ORDER_TYPE_BUY,
        "position": position.ticket,
        "price": tick.bid if is_buy else tick.ask,
        "deviation": TRADING.slippage_points,
        "magic": TRADING.magic_number,
        "comment": TRADING.comment + "_CLOSE",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }
    res = mt5.order_send(req)
    ok = res is not None and res.retcode == mt5.TRADE_RETCODE_DONE
    bus.log_trade({
        "action": "CLOSE",
        "symbol": symbol,
        "ticket": position.ticket,
        "ok": ok,
        "retcode": getattr(res, "retcode", None),
    })
    return ok


# ---------------------------------------------------------------------------
# Trailing stop
# ---------------------------------------------------------------------------
def maybe_trail(symbol: str, position, atr: float) -> None:
    if not MT5_AVAILABLE or position is None:
        return
    tick = mt5.symbol_info_tick(symbol)
    info = mt5.symbol_info(symbol)
    if not tick or not info:
        return
    is_buy = position.type == mt5.POSITION_TYPE_BUY
    price = tick.bid if is_buy else tick.ask
    r_distance = abs(position.price_open - position.sl) if position.sl else 0.0
    if r_distance <= 0:
        return
    move = (price - position.price_open) if is_buy else (position.price_open - price)
    if move < r_distance * TRADING.trail_activate_rr:
        return
    trail_distance = atr * TRADING.trail_atr_mult
    if is_buy:
        new_sl = price - trail_distance
        if new_sl > position.sl + info.point:
            modify_sl(symbol, position, new_sl)
    else:
        new_sl = price + trail_distance
        if new_sl < position.sl - info.point or position.sl == 0.0:
            modify_sl(symbol, position, new_sl)


# ---------------------------------------------------------------------------
# Daily circuit breaker
# ---------------------------------------------------------------------------
STATE_FILE = STATE_DIR / "trader_state.json"


def _load_state() -> Dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_state(state: Dict) -> None:
    try:
        STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")
    except OSError:
        pass


def daily_drawdown_hit(equity: float) -> bool:
    state = _load_state()
    today = datetime.utcnow().strftime("%Y-%m-%d")
    if state.get("date") != today:
        state = {"date": today, "open_equity": equity}
        _save_state(state)
        return False
    open_eq = float(state.get("open_equity") or equity)
    if open_eq <= 0:
        return False
    dd = (open_eq - equity) / open_eq
    return dd >= TRADING.max_daily_dd


# ---------------------------------------------------------------------------
# Main engine
# ---------------------------------------------------------------------------
def initialize() -> bool:
    if not MT5_AVAILABLE:
        bus.log("trader", "MetaTrader5 module not installed - running in DRY mode", level="WARN")
        return False
    if not mt5.initialize():
        bus.log("trader", f"MT5 initialize failed: {mt5.last_error()}", level="ERROR")
        return False
    info = mt5.account_info()
    if info is None:
        bus.log("trader", "MT5 account not logged in", level="ERROR")
        return False
    bus.log("trader", f"MT5 connected: account #{info.login}, equity={info.equity:.2f} {info.currency}")
    return True


def evaluate_symbol(symbol: str) -> Optional[Confluence]:
    df_ltf = fetch_rates(symbol, TRADING.timeframe_minutes, TRADING.history_bars)
    df_htf = fetch_rates(symbol, TRADING.htf_minutes, max(220, TRADING.history_bars // 3))
    if df_ltf is None or df_htf is None or df_ltf.empty:
        return None
    ltf = analyze(df_ltf)
    bias = htf_bias(df_htf)
    price = float(df_ltf["close"].iloc[-1])
    conf = score_confluence(ltf, bias, price)
    bus.log_signal(
        symbol=symbol,
        direction=conf.direction,
        confluence=conf.score,
        price=price,
        bias=bias,
        atr=ltf.atr,
        sweep=ltf.sweep,
        pd=ltf.premium_discount,
        reasons=";".join(conf.reasons),
    )
    return conf


def trade_loop() -> None:
    if not initialize():
        bus.log("trader", "Aborting trade loop - MT5 not initialized", level="ERROR")
        return
    bus.log("trader", "Trading loop armed")
    try:
        while True:
            account = mt5.account_info()
            if account is None:
                bus.log("trader", "Lost account info", level="ERROR")
                time.sleep(5)
                continue
            bus.log_equity(account.balance, account.equity)

            if account.equity >= TRADING.target_balance and TRADING.start_balance <= account.balance:
                bus.log("trader", f"Target {TRADING.target_balance}{account.currency} reached - standing down")
                time.sleep(TRADING.poll_interval_sec * 5)
                continue

            if daily_drawdown_hit(account.equity):
                bus.log("trader", f"Daily DD limit {TRADING.max_daily_dd:.0%} hit - halted", level="WARN")
                time.sleep(60)
                continue

            for symbol in TRADING.symbols:
                pos = current_position(symbol)
                df_ltf = fetch_rates(symbol, TRADING.timeframe_minutes, TRADING.history_bars)
                if df_ltf is None:
                    continue
                ltf = analyze(df_ltf)

                if pos is not None:
                    maybe_trail(symbol, pos, ltf.atr)
                    continue

                if len([p for p in (mt5.positions_get() or []) if p.magic == TRADING.magic_number]) >= TRADING.max_concurrent:
                    continue

                if is_news_blackout(symbol, TRADING.news_blackout_minutes):
                    bus.log("trader", f"{symbol} blocked by news-blackout", level="WARN")
                    continue

                conf = evaluate_symbol(symbol)
                if conf is None or conf.direction == "NONE":
                    continue
                if conf.score < TRADING.min_confluence:
                    continue

                price = float(df_ltf["close"].iloc[-1])
                plan = build_risk_plan(symbol, conf.direction, price, ltf.atr, account.equity)
                if plan is None:
                    bus.log("trader", f"{symbol}: cannot size trade", level="WARN")
                    continue
                bus.log(
                    "trader",
                    f"FIRE {conf.direction} {symbol} lots={plan.lots} sl={plan.sl:.5f} tp={plan.tp:.5f} conf={conf.score:.0%}",
                )
                send_order(symbol, conf.direction, plan.lots, plan.sl, plan.tp)

            time.sleep(TRADING.poll_interval_sec)
    except KeyboardInterrupt:
        bus.log("trader", "KeyboardInterrupt - shutting down")
    finally:
        if MT5_AVAILABLE:
            mt5.shutdown()


def dry_run_once() -> None:
    """Useful for unit-style debugging without a broker connection - runs the
    SMC engine on synthetic data and logs the resulting confluence."""
    import numpy as np
    rng = np.random.default_rng(7)
    n = 400
    base = 1.10 + np.cumsum(rng.normal(0, 0.0004, n))
    df = pd.DataFrame({
        "open": base + rng.normal(0, 0.0001, n),
        "high": base + np.abs(rng.normal(0, 0.0006, n)),
        "low": base - np.abs(rng.normal(0, 0.0006, n)),
        "close": base + rng.normal(0, 0.0002, n),
    })
    df["high"] = df[["open", "high", "close"]].max(axis=1)
    df["low"] = df[["open", "low", "close"]].min(axis=1)
    ltf = analyze(df)
    conf = score_confluence(ltf, htf_bias(df.tail(220)), float(df["close"].iloc[-1]))
    bus.log("trader", f"DRY-RUN conf={conf.score:.2f} dir={conf.direction} reasons={conf.reasons}")


if __name__ == "__main__":
    if "--dry" in sys.argv or not MT5_AVAILABLE:
        dry_run_once()
    else:
        trade_loop()
