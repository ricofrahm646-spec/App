from textwrap import dedent


def forex_signal_strategy() -> str:
    """Return a Pine Script strategy template with webhook-ready alerts."""

    return dedent(
        """
        //@version=5
        strategy("JARVIS Forex Signal Template", overlay=true, initial_capital=10000)

        fastLength = input.int(9, "Fast EMA")
        slowLength = input.int(21, "Slow EMA")
        atrLength = input.int(14, "ATR")
        riskReward = input.float(2.0, "Risk Reward", minval=0.5)

        fast = ta.ema(close, fastLength)
        slow = ta.ema(close, slowLength)
        atr = ta.atr(atrLength)

        buySignal = ta.crossover(fast, slow)
        sellSignal = ta.crossunder(fast, slow)

        longStop = close - atr
        longTarget = close + atr * riskReward
        shortStop = close + atr
        shortTarget = close - atr * riskReward

        plot(fast, color=color.teal)
        plot(slow, color=color.orange)
        plotshape(buySignal, title="Buy", text="BUY", style=shape.labelup, color=color.green)
        plotshape(sellSignal, title="Sell", text="SELL", style=shape.labeldown, color=color.red)

        if buySignal
            strategy.entry("JARVIS Buy", strategy.long)
            strategy.exit("JARVIS Buy Exit", "JARVIS Buy", stop=longStop, limit=longTarget)
            alert('{"symbol":"' + syminfo.ticker + '","side":"buy","price":' + str.tostring(close) + ',"timeframe":"' + timeframe.period + '","strategy":"jarvis_forex_template","stop_loss":' + str.tostring(longStop) + ',"take_profit":' + str.tostring(longTarget) + '}', alert.freq_once_per_bar_close)

        if sellSignal
            strategy.entry("JARVIS Sell", strategy.short)
            strategy.exit("JARVIS Sell Exit", "JARVIS Sell", stop=shortStop, limit=shortTarget)
            alert('{"symbol":"' + syminfo.ticker + '","side":"sell","price":' + str.tostring(close) + ',"timeframe":"' + timeframe.period + '","strategy":"jarvis_forex_template","stop_loss":' + str.tostring(shortStop) + ',"take_profit":' + str.tostring(shortTarget) + '}', alert.freq_once_per_bar_close)
        """
    ).strip()
