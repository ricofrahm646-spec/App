"""
MT5 M1 scalping helper with SMC-style heuristics (FVG, order blocks, liquidity sweeps).
Live trading can lose money. This is not investment advice. No performance is guaranteed.
"""
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from config import (
    CONFLUENCE_MIN,
    LOGS_DIR,
    MT5_LOGIN,
    MT5_MAGIC,
    MT5_PASSWORD,
    MT5_SERVER,
    MT5_SYMBOL,
    NEWS_SKIP_HOURS,
    RISK_PCT,
)

LOGS_DIR.mkdir(parents=True, exist_ok=True)
log = logging.getLogger("trader_ultimate")

try:
    import MetaTrader5 as mt5  # type: ignore
except ImportError:
    mt5 = None  # type: ignore


EQUITY_LOG = LOGS_DIR / "equity.jsonl"
SIGNAL_LOG = LOGS_DIR / "signals.jsonl"


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, default=str) + "\n")


@dataclass
class SMCState:
    bullish_fvg: bool
    bearish_fvg: bool
    bullish_ob: bool
    bearish_ob: bool
    bullish_sweep: bool
    bearish_sweep: bool
    confluence: float


def _ensure_df(rates: list[Any]) -> pd.DataFrame:
    df = pd.DataFrame(
        list(rates),
        columns=["time", "open", "high", "low", "close", "tick_volume", "spread", "real_volume"],
    )
    df["time"] = pd.to_datetime(df["time"], unit="s", utc=True)
    for col in ("open", "high", "low", "close"):
        df[col] = df[col].astype(float)
    return df.reset_index(drop=True)


def detect_fvg(df: pd.DataFrame, lookback: int = 3) -> tuple[bool, bool]:
    """3-candle fair value gap: bullish if low[i] > high[i-2]; bearish if high[i] < low[i-2]."""
    if len(df) < lookback + 2:
        return False, False
    i = len(df) - 2
    bull = float(df.loc[i, "low"]) > float(df.loc[i - 2, "high"])
    bear = float(df.loc[i, "high"]) < float(df.loc[i - 2, "low"])
    return bull, bear


def swing_points(df: pd.DataFrame, left: int = 2, right: int = 2) -> tuple[pd.Series, pd.Series]:
    highs = df["high"]
    lows = df["low"]
    swing_high = highs[(highs.shift(left) < highs) & (highs.shift(-right) < highs)]
    swing_low = lows[(lows.shift(left) > lows) & (lows.shift(-right) > lows)]
    return swing_high, swing_low


def detect_liquidity_sweep(df: pd.DataFrame) -> tuple[bool, bool]:
    """Wick beyond recent swing then close back inside range (simplified)."""
    if len(df) < 20:
        return False, False
    sh, sl = swing_points(df.tail(80))
    if sh.empty or sl.empty:
        return False, False
    last = df.iloc[-1]
    prev = df.iloc[-2]
    recent_high = float(sh.dropna().iloc[-1])
    recent_low = float(sl.dropna().iloc[-1])
    bull_sweep = float(prev["low"]) < recent_low and float(last["close"]) > recent_low
    bear_sweep = float(prev["high"]) > recent_high and float(last["close"]) < recent_high
    return bull_sweep, bear_sweep


def detect_order_blocks(df: pd.DataFrame, impulse: int = 5) -> tuple[bool, bool]:
    """
    Last opposite candle before impulse move (very simplified OB proxy).
    Bullish OB: last bearish candle before a run of higher closes.
    """
    if len(df) < impulse + 6:
        return False, False
    tail = df.tail(impulse + 6).reset_index(drop=True)
    bull_ob = False
    bear_ob = False
    for i in range(2, len(tail) - impulse):
        window = tail.iloc[i : i + impulse]
        up_move = window["close"].iloc[-1] > window["open"].iloc[0] * 1.0003
        down_move = window["close"].iloc[-1] < window["open"].iloc[0] * 0.9997
        prev = tail.iloc[i - 1]
        if up_move and prev["close"] < prev["open"]:
            bull_ob = True
        if down_move and prev["close"] > prev["open"]:
            bear_ob = True
    return bull_ob, bear_ob


def confluence_score(state: SMCState) -> float:
    parts = [
        state.bullish_fvg or state.bearish_fvg,
        state.bullish_ob or state.bearish_ob,
        state.bullish_sweep or state.bearish_sweep,
    ]
    return sum(1 for p in parts if p) / max(len(parts), 1)


def news_protection_active(now: datetime | None = None) -> bool:
    """
    Skip new trades during configured UTC hours (env NEWS_SKIP_HOURS).
    For production, plug in a licensed economic calendar API.
    """
    raw = (NEWS_SKIP_HOURS or "").strip()
    if not raw:
        return False
    now = now or datetime.now(timezone.utc)
    hours = {int(x) for x in raw.split(",") if x.strip().isdigit()}
    return now.hour in hours


def mt5_connect() -> bool:
    if mt5 is None:
        log.warning("MetaTrader5 package not installed.")
        return False
    kwargs: dict[str, Any] = {}
    if MT5_LOGIN and MT5_PASSWORD and MT5_SERVER:
        kwargs = {"login": MT5_LOGIN, "password": MT5_PASSWORD, "server": MT5_SERVER}
    if not mt5.initialize(**kwargs):
        log.error("MT5 initialize failed: %s", mt5.last_error())
        return False
    return True


def fetch_rates(symbol: str, n: int = 500) -> pd.DataFrame | None:
    if mt5 is None or not mt5.terminal_info():
        return None
    rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 0, n)
    if rates is None or len(rates) == 0:
        log.error("No rates: %s", mt5.last_error())
        return None
    return _ensure_df(rates)


def account_equity() -> float | None:
    if mt5 is None:
        return None
    ai = mt5.account_info()
    if ai is None:
        return None
    return float(ai.equity)


def lot_from_risk(symbol: str, risk_pct: float) -> float:
    if mt5 is None:
        return 0.01
    ai = mt5.account_info()
    if ai is None:
        return 0.01
    equity = float(ai.equity)
    info = mt5.symbol_info(symbol)
    if info is None or info.trade_tick_size <= 0:
        return round(max(info.volume_min if info else 0.01, 0.01), 2)
    risk_money = equity * (risk_pct / 100.0)
    tick_value = info.trade_tick_value
    sl_points = max(info.point * 200, info.point * 10)
    denom = (sl_points / info.trade_tick_size) * tick_value if tick_value else 1.0
    lots = risk_money / max(denom, 1e-9)
    vol_min = info.volume_min
    vol_max = info.volume_max
    step = info.volume_step
    lots = max(vol_min, min(vol_max, round(lots / step) * step))
    return float(round(lots, 2))


def trail_positions(symbol: str, trail_points: float = 150) -> None:
    """Move SL following favorable price (points in price units, not pips)."""
    if mt5 is None:
        return
    positions = mt5.positions_get(symbol=symbol)
    if not positions:
        return
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        return
    info = mt5.symbol_info(symbol)
    if info is None:
        return
    point = float(info.point) if info.point else 0.0001
    dist = trail_points * point
    for pos in positions:
        if pos.magic != MT5_MAGIC:
            continue
        if pos.type == mt5.ORDER_TYPE_BUY:
            new_sl = max(float(pos.sl or 0), tick.bid - dist)
            if new_sl > float(pos.sl or 0):
                req = {
                    "action": mt5.TRADE_ACTION_SLTP,
                    "position": pos.ticket,
                    "symbol": symbol,
                    "sl": new_sl,
                    "tp": pos.tp,
                }
                mt5.order_send(req)
        else:
            new_sl = min(float(pos.sl or 1e9), tick.ask + dist) if pos.sl else tick.ask + dist
            if pos.sl is None or new_sl < float(pos.sl):
                req = {
                    "action": mt5.TRADE_ACTION_SLTP,
                    "position": pos.ticket,
                    "symbol": symbol,
                    "sl": new_sl,
                    "tp": pos.tp,
                }
                mt5.order_send(req)


def send_market_order(symbol: str, direction: str, volume: float, sl_pct: float = 0.15) -> dict[str, Any]:
    if mt5 is None:
        return {"ok": False, "error": "mt5_missing"}
    info = mt5.symbol_info(symbol)
    if info is None or not info.visible:
        mt5.symbol_select(symbol, True)
        info = mt5.symbol_info(symbol)
    tick = mt5.symbol_info_tick(symbol)
    if info is None or tick is None:
        return {"ok": False, "error": "symbol"}
    point = float(info.point) or 0.0001
    price = tick.ask if direction == "buy" else tick.bid
    sl_dist = max(50 * point, price * (sl_pct / 100.0))
    if direction == "buy":
        sl = price - sl_dist
        order_type = mt5.ORDER_TYPE_BUY
    else:
        sl = price + sl_dist
        order_type = mt5.ORDER_TYPE_SELL
    fm = int(info.filling_mode or 0)
    ioc = getattr(mt5, "SYMBOL_FILLING_IOC", 2)
    fok = getattr(mt5, "SYMBOL_FILLING_FOK", 1)
    if fm & ioc:
        filling = mt5.ORDER_FILLING_IOC
    elif fm & fok:
        filling = mt5.ORDER_FILLING_FOK
    else:
        filling = mt5.ORDER_FILLING_RETURN
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": volume,
        "type": order_type,
        "price": price,
        "sl": sl,
        "tp": 0.0,
        "deviation": 20,
        "magic": MT5_MAGIC,
        "comment": "jarvis_smc",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": filling,
    }
    res = mt5.order_send(request)
    ok = res is not None and res.retcode == mt5.TRADE_RETCODE_DONE
    return {"ok": ok, "retcode": getattr(res, "retcode", None), "comment": getattr(res, "comment", "")}


def evaluate_smc(df: pd.DataFrame) -> tuple[SMCState, str]:
    bf, sfv = detect_fvg(df)
    bb, bo = detect_order_blocks(df)
    bs, ss = detect_liquidity_sweep(df)
    state = SMCState(
        bullish_fvg=bf,
        bearish_fvg=sfv,
        bullish_ob=bb,
        bearish_ob=bo,
        bullish_sweep=bs,
        bearish_sweep=ss,
        confluence=0.0,
    )
    state.confluence = confluence_score(state)
    bias = "flat"
    if bf and bb and bs:
        bias = "long"
    if sfv and bo and ss:
        bias = "short"
    return state, bias


def run_once(symbol: str = MT5_SYMBOL) -> dict[str, Any]:
    """Single evaluation cycle: signals, optional order, trail, logging."""
    if not mt5_connect():
        return {"connected": False, "reason": "mt5_init"}
    try:
        eq = account_equity()
        if eq is not None:
            append_jsonl(EQUITY_LOG, {"ts": datetime.now(timezone.utc).isoformat(), "equity": eq})

        if news_protection_active():
            msg = "news_protection_window"
            log.info(msg)
            append_jsonl(SIGNAL_LOG, {"ts": datetime.now(timezone.utc).isoformat(), "skipped": msg})
            return {"connected": True, "skipped": msg}

        df = fetch_rates(symbol)
        if df is None:
            return {"connected": True, "error": "no_data"}
        state, bias = evaluate_smc(df)
        row = asdict(state)
        row.update({"ts": datetime.now(timezone.utc).isoformat(), "symbol": symbol, "bias": bias})
        append_jsonl(SIGNAL_LOG, row)

        trail_positions(symbol)

        if state.confluence < CONFLUENCE_MIN:
            return {"connected": True, "bias": bias, "confluence": state.confluence, "trade": "hold"}

        vol = lot_from_risk(symbol, RISK_PCT)
        if bias == "long":
            out = send_market_order(symbol, "buy", vol)
        elif bias == "short":
            out = send_market_order(symbol, "sell", vol)
        else:
            out = {"ok": False, "error": "no_aligned_bias"}
        return {
            "connected": True,
            "bias": bias,
            "confluence": state.confluence,
            "trade": out,
        }
    finally:
        if mt5:
            mt5.shutdown()


def run_loop(interval_sec: float = 5.0, symbol: str = MT5_SYMBOL) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    while True:
        try:
            log.info("tick: %s", run_once(symbol))
        except Exception:  # noqa: BLE001
            log.exception("cycle error")
        time.sleep(interval_sec)


if __name__ == "__main__":
    run_loop()
