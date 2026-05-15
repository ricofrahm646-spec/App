module PerformanceAudit

using Dates
using DataFrames
using CSV

export track_signal, SignalRecord

struct SignalRecord
    timestamp::DateTime
    strategy::Symbol
    direction::Symbol
    entry_price::Float64
    stop_loss::Float64
    take_profit::Float64
    r_multiple::Float64
end

function track_signal(record::SignalRecord, file_path="OMEGA-TRADER/data/trade_history.csv")
    # Ensure data directory exists
    mkpath(dirname(file_path))

    df = DataFrame(
        Timestamp = [record.timestamp],
        Strategy = [string(record.strategy)],
        Direction = [string(record.direction)],
        Entry = [record.entry_price],
        SL = [record.stop_loss],
        TP = [record.take_profit],
        R_Multiple = [record.r_multiple]
    )

    if isfile(file_path)
        CSV.write(file_path, df, append=true)
    else
        CSV.write(file_path, df)
    end
end

function calculate_r_multiple(entry, sl, tp)
    risk = abs(entry - sl)
    reward = abs(tp - entry)
    if risk == 0 return 0.0 end
    return round(reward / risk, digits=2)
end

end
