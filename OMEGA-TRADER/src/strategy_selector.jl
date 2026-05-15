module StrategySelector

using Statistics

export select_strategy

function atr(highs, lows, closes, period=14)
    n = length(closes)
    if n < period + 1
        return 0.0
    end

    tr = zeros(n-1)
    for i in 1:n-1
        tr[i] = max(highs[i+1] - lows[i+1], abs(highs[i+1] - closes[i]), abs(lows[i+1] - closes[i]))
    end

    return mean(tr[end-period+1:end])
end

function select_strategy(highs, lows, closes)
    current_atr = atr(highs, lows, closes)

    # Simple logic based on ATR relative to price
    volatility_ratio = current_atr / closes[end]

    if volatility_ratio > 0.002 # High volatility
        return :SMC
    elseif volatility_ratio < 0.0005 # Low volatility
        return :MeanReversion
    else
        return :TrendFollowing
    end
end

end
