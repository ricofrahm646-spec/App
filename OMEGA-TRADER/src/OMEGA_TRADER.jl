module OMEGA_TRADER

include("strategies/smc.jl")
include("strategies/mean_reversion.jl")
include("strategies/trend_following.jl")
include("risk_management.jl")
include("strategy_selector.jl")
include("performance_audit.jl")
include("dashboard.jl")

using .SMCStrategy
using .MeanReversionStrategy
using .TrendFollowingStrategy
using .RiskManagement
using .StrategySelector
using .PerformanceAudit
using .Dashboard
using Dates

export run_system

function run_system(market_data, account_balance, risk_pct, sl_pips)
    # 1. Strategy Selection
    highs = market_data.high
    lows = market_data.low
    opens = market_data.open
    closes = market_data.close

    active_strat_sym = StrategySelector.select_strategy(highs, lows, closes)

    # 2. Risk Management
    risk_cfg = RiskConfig(account_balance, risk_pct, sl_pips, 4.0, 0.0) # 4% daily limit
    dd_status = RiskManagement.check_drawdown(risk_cfg)

    if dd_status == :locked
        println("TRADING LOCKED: Daily Drawdown Limit Reached.")
        return
    end

    lot_size = RiskManagement.calculate_lot_size(risk_cfg)

    # 3. Signal Generation
    signal = :none
    if active_strat_sym == :SMC
        signal = SMCStrategy.detect_orderblock(highs, lows, opens, closes)
    elseif active_strat_sym == :MeanReversion
        signal = MeanReversionStrategy.detect_mean_reversion(closes)
    elseif active_strat_sym == :TrendFollowing
        signal = TrendFollowingStrategy.detect_trend_following(closes)
    end

    # 4. Performance Audit (if signal exists)
    if signal != :none
        # Determine pip multiplier (0.01 for JPY/Gold, 0.0001 for others - simplified)
        pip_mult = closes[end] > 500 ? 0.01 : 0.0001

        tp_price = signal == :buy || signal == :bullish_ob ? closes[end] + (sl_pips * pip_mult * 2) : closes[end] - (sl_pips * pip_mult * 2)
        sl_price = signal == :buy || signal == :bullish_ob ? closes[end] - (sl_pips * pip_mult) : closes[end] + (sl_pips * pip_mult)

        r_multiple = PerformanceAudit.calculate_r_multiple(closes[end], sl_price, tp_price)

        record = SignalRecord(
            now(),
            active_strat_sym,
            signal,
            closes[end],
            sl_price,
            tp_price,
            r_multiple
        )
        PerformanceAudit.track_signal(record)
    end

    # 5. Dashboard Update
    stats = (
        drawdown_status = dd_status,
        active_strategy = active_strat_sym,
        balance = account_balance,
        daily_loss = 0.0,
        prop_firm_status = "In Progress (Limit 4%)",
        last_signal_dir = signal,
        last_signal_price = closes[end]
    )

    Dashboard.display_dashboard(stats)
end

end
