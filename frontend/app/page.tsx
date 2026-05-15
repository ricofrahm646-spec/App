"use client";

import { useEffect, useState } from "react";
import { ChatPanel } from "../components/ChatPanel";
import { MetricCard } from "../components/MetricCard";

type DashboardSummary = {
  account: {
    balance: number;
    equity: number;
    margin: number;
    free_margin: number;
    drawdown_percent: number;
    currency: string;
  };
  metrics: {
    winrate: number;
    total_trades: number;
    winning_trades: number;
    losing_trades: number;
    profit_factor: number;
    drawdown: number;
  };
  ai_status: Array<{ name: string; enabled: boolean; purpose: string }>;
  strategy_status: Array<{ name: string; archetype: string; risk_profile: string }>;
  open_trades: Array<Record<string, string | number>>;
  live_market_analysis: { phase: string; notes: string[] };
};

const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export default function Home() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);

  useEffect(() => {
    async function loadSummary() {
      const result = await fetch(`${apiBase}/api/dashboard/summary`, { cache: "no-store" });
      setSummary(await result.json());
    }

    loadSummary().catch(() => setSummary(null));
    const interval = window.setInterval(() => {
      loadSummary().catch(() => setSummary(null));
    }, 10_000);
    return () => window.clearInterval(interval);
  }, []);

  const account = summary?.account;
  const metrics = summary?.metrics;

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top_right,_rgba(61,214,198,0.18),_transparent_35%),#08111f] px-6 py-8">
      <div className="mx-auto max-w-7xl">
        <header className="flex flex-col gap-4 border-b border-white/10 pb-8 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="text-sm uppercase tracking-[0.35em] text-jarvis-accent">JARVIS</p>
            <h1 className="mt-3 text-4xl font-black md:text-6xl">AI Trading Operating System</h1>
            <p className="mt-4 max-w-3xl text-slate-300">
              Modulare Plattform fuer Strategie-Generierung, Backtesting, MT5-Steuerung,
              Telegram-Signale, TradingView-Webhooks und kontrolliertes Risiko.
            </p>
          </div>
          <div className="rounded-2xl border border-jarvis-accent/30 bg-jarvis-accent/10 px-5 py-3 text-jarvis-accent">
            Live Trading: Environment-gated
          </div>
        </header>

        <section className="mt-8 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <MetricCard label="Balance" value={`${account?.balance ?? 0} ${account?.currency ?? "USD"}`} />
          <MetricCard label="Equity" value={`${account?.equity ?? 0} ${account?.currency ?? "USD"}`} />
          <MetricCard label="Margin" value={account?.margin ?? 0} />
          <MetricCard label="Drawdown" value={`${account?.drawdown_percent ?? 0}%`} />
          <MetricCard label="Winrate" value={`${metrics?.winrate ?? 0}%`} />
          <MetricCard label="Gesamttrades" value={metrics?.total_trades ?? 0} />
          <MetricCard label="Profit Factor" value={metrics?.profit_factor ?? 0} />
          <MetricCard label="Freie Margin" value={account?.free_margin ?? 0} />
        </section>

        <section className="mt-8 grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
          <ChatPanel />
          <div className="space-y-6">
            <Panel title="KI-Status">
              <ul className="space-y-3">
                {summary?.ai_status.map((capability) => (
                  <li key={capability.name} className="rounded-xl bg-white/5 p-3">
                    <div className="flex justify-between">
                      <span className="font-semibold">{capability.name}</span>
                      <span className={capability.enabled ? "text-jarvis-accent" : "text-slate-500"}>
                        {capability.enabled ? "aktiv" : "optional"}
                      </span>
                    </div>
                    <p className="mt-1 text-sm text-slate-400">{capability.purpose}</p>
                  </li>
                )) ?? <li className="text-slate-400">Backend nicht verbunden.</li>}
              </ul>
            </Panel>

            <Panel title="Live-Marktanalyse">
              <p className="text-2xl font-semibold text-jarvis-accent">
                {summary?.live_market_analysis.phase ?? "offline"}
              </p>
              <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-slate-400">
                {summary?.live_market_analysis.notes.map((note) => <li key={note}>{note}</li>) ?? null}
              </ul>
            </Panel>
          </div>
        </section>

        <section className="mt-8 grid gap-6 lg:grid-cols-2">
          <Panel title="Offene Trades">
            <pre className="overflow-auto rounded-xl bg-black/30 p-4 text-sm text-slate-300">
              {JSON.stringify(summary?.open_trades ?? [], null, 2)}
            </pre>
          </Panel>
          <Panel title="Strategiestatus">
            <pre className="overflow-auto rounded-xl bg-black/30 p-4 text-sm text-slate-300">
              {JSON.stringify(summary?.strategy_status ?? [], null, 2)}
            </pre>
          </Panel>
        </section>
      </div>
    </main>
  );
}

function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="rounded-3xl border border-white/10 bg-jarvis-panel p-6">
      <h2 className="mb-4 text-xl font-bold">{title}</h2>
      {children}
    </section>
  );
}
