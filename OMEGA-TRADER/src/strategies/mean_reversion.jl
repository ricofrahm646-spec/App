module MeanReversionStrategy

using Statistics

export detect_mean_reversion

"""
RSI calculation.
"""
function rsi(prices, period=14)
    if length(prices) < period + 1
        return fill(50.0, length(prices))
    end

    deltas = diff(prices)
    gains = [d > 0 ? d : 0.0 for d in deltas]
    losses = [d < 0 ? -d : 0.0 for d in deltas]

    avg_gain = mean(gains[1:period])
    avg_loss = mean(losses[1:period])

    rsis = zeros(length(prices))

    for i in (period+1):length(prices)
        if i > period + 1
            avg_gain = (avg_gain * (period - 1) + gains[i-1]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i-1]) / period
        end

        if avg_loss == 0
            rsis[i] = 100.0
        else
            rs = avg_gain / avg_loss
            rsis[i] = 100.0 - (100.0 / (1.0 + rs))
        end
    end
    return rsis
end

"""
Bollinger Bands calculation.
"""
function bollinger_bands(prices, period=20, std_dev=2.0)
    if length(prices) < period
        return (nothing, nothing, nothing)
    end
    sma = mean(prices[end-period+1:end])
    sd = std(prices[end-period+1:end])
    return (sma, sma + std_dev * sd, sma - std_dev * sd)
end

function detect_mean_reversion(prices)
    rsis = rsi(prices)
    current_rsi = rsis[end]
    sma, upper, lower = bollinger_bands(prices)

    if isnothing(sma) return :none end

    current_price = prices[end]

    if current_rsi < 30 && current_price <= lower
        return :buy
    elseif current_rsi > 70 && current_price >= upper
        return :sell
    end

    return :none
end

end
