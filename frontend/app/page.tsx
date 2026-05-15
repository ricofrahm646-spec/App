"use client";

import { useEffect, useState } from "react";

import { ChatPanel } from "@/components/chat-panel";
import { MetricCard } from "@/components/metric-card";
import { ModuleStatus } from "@/components/module-status";
import { TradeTable } from "@/components/trade-table";
import { fetchOverview, type SystemOverview } from "@/lib/api";

export default function Home() {
  const [overview, setOverview] = useState<SystemOverview | null>(null);

  useEffect(() => {
    void fetchOverview().then(setOverview);
  }, []);

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-7xl flex-col px-6 py-10 lg:px-10">
      <section className="grid gap-6 lg:grid-cols-[1.4fr_1fr]">
        <div className="space-y-6">
          <div className="rounded-3xl border border-white/10 bg-white/5 p-8 backdrop-blur">
            <p className="text-sm uppercase tracking-[0.2em] text-cyan-300">
              Full AI Trading Operating System
            </p>
            <h1 className="mt-4 max-w-3xl text-4xl font-semibold tracking-tight text-white lg:text-6xl">
              JARVIS orchestrates strategy creation, backtesting, risk control,
              MT5 automation, and operator workflows.
            </h1>
            <p className="mt-4 max-w-2xl text-base leading-7 text-slate-300">
              The platform foundation includes a FastAPI orchestration backend,
              a Next.js command dashboard, MQL5 generation, TradingView and
              Telegram integration stubs, PostgreSQL and Redis infrastructure,
              and a strict one-trade risk framework.
            </p>
          </div>

          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {(overview?.metrics ?? []).map((metric) => (
              <MetricCard key={metric.label} {...metric} />
            ))}
          </div>
        </div>

        <ChatPanel />
      </section>

      <section className="mt-10 grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
        <div className="rounded-3xl border border-white/10 bg-white/5 p-6 backdrop-blur">
          <div className="flex items-center justify-between gap-4">
            <div>
              <p className="text-sm uppercase tracking-[0.2em] text-slate-400">
                Module health
              </p>
              <h2 className="mt-2 text-2xl font-semibold text-white">
                Platform status
              </h2>
            </div>
            <div className="rounded-full bg-cyan-500/10 px-4 py-2 text-sm text-cyan-200 ring-1 ring-cyan-500/30">
              {overview?.ai_status ?? "Loading system state..."}
            </div>
          </div>

          <div className="mt-6 grid gap-4">
            {(overview?.modules ?? []).map((module) => (
              <ModuleStatus key={module.name} {...module} />
            ))}
          </div>
        </div>

        <div className="rounded-3xl border border-white/10 bg-white/5 p-6 backdrop-blur">
          <p className="text-sm uppercase tracking-[0.2em] text-slate-400">
            Active strategy
          </p>
          <h2 className="mt-2 text-2xl font-semibold text-white">
            {overview?.active_strategy ?? "Loading..."}
          </h2>
          <div className="mt-5 space-y-4 text-sm text-slate-300">
            <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
              <p className="font-medium text-white">Risk governance</p>
              <ul className="mt-2 space-y-2">
                <li>- Max 1 trade at a time</li>
                <li>- No simultaneous Buy and Sell exposure</li>
                <li>- Emergency close at configured loss threshold</li>
                <li>- Backtest review before any live rollout</li>
              </ul>
            </div>
            <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
              <p className="font-medium text-white">Integrated domains</p>
              <ul className="mt-2 space-y-2">
                <li>- AI planning and file generation</li>
                <li>- MT5 connector and MQL5 template pipeline</li>
                <li>- Telegram notifications</li>
                <li>- TradingView webhook workflows</li>
              </ul>
            </div>
          </div>
        </div>
      </section>

      <section className="mt-10 rounded-3xl border border-white/10 bg-white/5 p-6 backdrop-blur">
        <div className="flex items-center justify-between gap-4">
          <div>
            <p className="text-sm uppercase tracking-[0.2em] text-slate-400">
              Execution monitor
            </p>
            <h2 className="mt-2 text-2xl font-semibold text-white">
              Trades and position guardrails
            </h2>
          </div>
        </div>
        <div className="mt-6">
          <TradeTable trades={overview?.open_trades ?? []} />
        </div>
      </section>
    </main>
  );
}
