"use client";

import { useState } from "react";
import useSWR from "swr";
import { Card } from "@/components/Card";
import { EquityChart } from "@/components/EquityChart";
import { Shell } from "@/components/Shell";
import { Stat } from "@/components/Stat";
import { api, fetcher } from "@/lib/api";

type Result = {
  metrics: {
    trades: number;
    winrate_pct: number;
    profit_factor: number;
    max_drawdown_pct: number;
    sharpe: number;
    return_pct: number;
    final_balance: number;
  };
  equity_curve: number[];
};

export default function BacktestPage() {
  const { data: kinds } = useSWR<string[]>("/api/strategies/kinds", fetcher);
  const [strategy, setStrategy] = useState("trend_following");
  const [symbol, setSymbol] = useState("EURUSD");
  const [timeframe, setTimeframe] = useState("M15");
  const [bars, setBars] = useState(5000);
  const [result, setResult] = useState<Result | null>(null);
  const [running, setRunning] = useState(false);

  const run = async () => {
    setRunning(true);
    try {
      const r = await api<Result>("/api/backtest/run", {
        method: "POST",
        body: JSON.stringify({ strategy, symbol, timeframe, bars }),
      });
      setResult(r);
    } finally {
      setRunning(false);
    }
  };

  const chartData = (result?.equity_curve ?? []).map((eq, i) => ({
    t: i,
    equity: eq,
  }));

  return (
    <Shell>
      <h1 className="mb-1 text-2xl font-semibold">Backtest</h1>
      <p className="mb-6 text-sm text-slate-400">
        Vectorised backtest with spread + slippage simulation.
      </p>

      <Card className="mb-4">
        <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
          <label className="text-xs uppercase tracking-widest text-slate-400">
            Strategy
            <select
              value={strategy}
              onChange={(e) => setStrategy(e.target.value)}
              className="mt-1 w-full rounded-lg border border-jarvis-border bg-jarvis-bg px-3 py-2 text-sm text-slate-100"
            >
              {(kinds ?? []).map((k) => (
                <option key={k} value={k}>
                  {k}
                </option>
              ))}
            </select>
          </label>
          <label className="text-xs uppercase tracking-widest text-slate-400">
            Symbol
            <input
              value={symbol}
              onChange={(e) => setSymbol(e.target.value.toUpperCase())}
              className="mt-1 w-full rounded-lg border border-jarvis-border bg-jarvis-bg px-3 py-2 text-sm text-slate-100 font-mono"
            />
          </label>
          <label className="text-xs uppercase tracking-widest text-slate-400">
            Timeframe
            <select
              value={timeframe}
              onChange={(e) => setTimeframe(e.target.value)}
              className="mt-1 w-full rounded-lg border border-jarvis-border bg-jarvis-bg px-3 py-2 text-sm text-slate-100"
            >
              {["M1", "M5", "M15", "M30", "H1", "H4", "D1"].map((tf) => (
                <option key={tf}>{tf}</option>
              ))}
            </select>
          </label>
          <label className="text-xs uppercase tracking-widest text-slate-400">
            Bars
            <input
              type="number"
              value={bars}
              onChange={(e) => setBars(Number(e.target.value))}
              className="mt-1 w-full rounded-lg border border-jarvis-border bg-jarvis-bg px-3 py-2 text-sm text-slate-100 font-mono"
            />
          </label>
          <button
            onClick={run}
            disabled={running}
            className="mt-5 rounded-lg bg-jarvis-accent px-4 py-2 text-sm font-semibold text-slate-900 hover:bg-cyan-300 disabled:opacity-50"
          >
            {running ? "Running…" : "Run backtest"}
          </button>
        </div>
      </Card>

      {result && (
        <>
          <div className="mb-4 grid grid-cols-2 gap-3 md:grid-cols-6">
            <Card><Stat label="Trades" value={result.metrics.trades} /></Card>
            <Card><Stat label="Winrate" value={`${result.metrics.winrate_pct}`} unit="%" /></Card>
            <Card><Stat label="PF" value={result.metrics.profit_factor} /></Card>
            <Card>
              <Stat
                label="Max DD"
                value={`${result.metrics.max_drawdown_pct}`}
                unit="%"
                tone="bad"
              />
            </Card>
            <Card><Stat label="Sharpe" value={result.metrics.sharpe} /></Card>
            <Card>
              <Stat
                label="Return"
                value={`${result.metrics.return_pct}`}
                unit="%"
                tone={result.metrics.return_pct >= 0 ? "good" : "bad"}
              />
            </Card>
          </div>

          <Card title="Equity curve">
            <EquityChart data={chartData} />
          </Card>
        </>
      )}
    </Shell>
  );
}
