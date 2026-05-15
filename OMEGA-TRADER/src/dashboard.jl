module Dashboard

using Crayons

export display_dashboard

function display_dashboard(stats)
    blue = Crayon(foreground = :blue, bold = true)
    green = Crayon(foreground = :green)
    red = Crayon(foreground = :red)
    yellow = Crayon(foreground = :yellow)
    reset = Crayon(reset = true)

    println(blue, "================================================")
    println(blue, "           OMEGA-TRADER TERMINAL V1.0           ")
    println(blue, "================================================")

    status_color = stats.drawdown_status == :active ? green : red
    println("Status: ", status_color, stats.drawdown_status, reset)

    println("Current Strategy: ", yellow, stats.active_strategy, reset)
    println("Account Balance:  ", green, "\$", stats.balance, reset)
    println("Daily Loss:       ", red, "\$", stats.daily_loss, reset)
    println("Prop-Firm Status: ", blue, stats.prop_firm_status, reset)

    println(blue, "------------------------------------------------")
    println("Last Signal: ", stats.last_signal_dir, " @ ", stats.last_signal_price)
    println(blue, "------------------------------------------------")
    println(reset)
end

end
