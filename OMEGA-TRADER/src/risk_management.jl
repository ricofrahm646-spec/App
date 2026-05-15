module RiskManagement

export calculate_lot_size, check_drawdown, RiskConfig

struct RiskConfig
    balance::Float64
    risk_per_trade_percent::Float64
    stop_loss_pips::Float64
    daily_drawdown_limit::Float64
    current_daily_loss::Float64
end

function calculate_lot_size(config::RiskConfig)
    # Standard Lot calculation (assuming 1 pip = $10 for 1 lot on standard pairs)
    # Risk Amount = Balance * Risk%
    risk_amount = config.balance * (config.risk_per_trade_percent / 100.0)

    if config.stop_loss_pips <= 0
        return 0.0
    end

    # Lot Size = Risk Amount / (SL in pips * pip value)
    # Simple pip value assumption for this module
    pip_value = 10.0
    lot_size = risk_amount / (config.stop_loss_pips * pip_value)

    return round(lot_size, digits=2)
end

function check_drawdown(config::RiskConfig)
    max_loss = config.balance * (config.daily_drawdown_limit / 100.0)
    if config.current_daily_loss >= max_loss
        return :locked
    end
    return :active
end

end
