module TrendFollowingStrategy

using Statistics

export detect_trend_following

function ema(prices, period)
    n = length(prices)
    if n < period
        return prices
    end
    α = 2 / (period + 1)
    emas = zeros(n)
    emas[period] = mean(prices[1:period])
    for i in (period+1):n
        emas[i] = (prices[i] - emas[i-1]) * α + emas[i-1]
    end
    return emas
end

function macd(prices, fast=12, slow=26, signal=9)
    if length(prices) < slow + signal
        return (nothing, nothing)
    end
    ema_fast = ema(prices, fast)
    ema_slow = ema(prices, slow)
    macd_line = ema_fast .- ema_slow
    signal_line = ema(macd_line[slow:end], signal)
    return (macd_line[end], signal_line[end])
end

function detect_trend_following(prices)
    if length(prices) < 50
        return :none
    end

    ema8 = ema(prices, 8)[end]
    ema21 = ema(prices, 21)[end]

    macd_val, signal_val = macd(prices)

    if isnothing(macd_val) return :none end

    if ema8 > ema21 && macd_val > signal_val
        return :buy
    elseif ema8 < ema21 && macd_val < signal_val
        return :sell
    end

    return :none
end

end
