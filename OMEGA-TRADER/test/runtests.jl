using Test
include("../src/OMEGA_TRADER.jl")
using .OMEGA_TRADER

@testset "OMEGA-TRADER Tests" begin
    @testset "Risk Management" begin
        using .OMEGA_TRADER.RiskManagement
        cfg = RiskConfig(10000.0, 1.0, 20.0, 4.0, 0.0)
        lot = calculate_lot_size(cfg)
        @test lot > 0
        @test check_drawdown(cfg) == :active

        fail_cfg = RiskConfig(10000.0, 1.0, 20.0, 4.0, 500.0)
        @test check_drawdown(fail_cfg) == :locked
    end

    @testset "Strategy Selector" begin
        using .OMEGA_TRADER.StrategySelector
        highs = [1.1, 1.11, 1.12, 1.13, 1.14]
        lows = [1.09, 1.10, 1.11, 1.12, 1.13]
        closes = [1.1, 1.11, 1.12, 1.13, 1.14]
        strat = select_strategy(highs, lows, closes)
        @test strat in [:SMC, :MeanReversion, :TrendFollowing]
    end

    @testset "Performance Audit" begin
        using .OMEGA_TRADER.PerformanceAudit
        r = calculate_r_multiple(1.1000, 1.0900, 1.1200)
        @test r == 2.0
    end
end
