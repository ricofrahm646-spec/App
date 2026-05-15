module SMCStrategy

using Statistics

export detect_orderblock

"""
Detects Orderblocks (SMC).
Simplistic implementation:
- Bullish OB: Last down candle before a strong move up.
- Bearish OB: Last up candle before a strong move down.
"""
function detect_orderblock(highs, lows, opens, closes)
    n = length(closes)
    if n < 3
        return :none
    end

    # Check for Bullish OB
    # Last candle was bearish, current is strongly bullish and breaks previous high
    if closes[n-1] < opens[n-1] && closes[n] > opens[n] && closes[n] > highs[n-1]
        return :bullish_ob
    end

    # Check for Bearish OB
    if closes[n-1] > opens[n-1] && closes[n] < opens[n] && closes[n] < lows[n-1]
        return :bearish_ob
    end

    return :none
end

end
