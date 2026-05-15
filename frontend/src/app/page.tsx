"use client";

import { useEffect, useState } from "react";
import useSWR from "swr";

import { Card } from "@/components/Card";
import { Shell } from "@/components/Shell";
import { Stat } from "@/components/Stat";
import { EquityChart } from "@/components/EquityChart";
import { fetcher } from "@/lib/api";
import { useWebSocket } from "@/lib/ws";

type Account = {
  balance: number;
  equity: number;
  margin: number;
  free_margin: number;
  profit: number;
  currency: string;
  server: string | null;
};

type Trade = {
  ticket: number | null;
  symbol: string;
  side: "BUY" | "SELL";
  volume: number;
  entry_price: number;
  profit: number;
  status: string;
};

export default function DashboardPage() {
  const ws = useWebSocket();
  const { data: status } = useSWR("/api/system/status", fetcher, {
    refreshInterval: 5000,
  });

  const account = (ws["account"] as Account | undefined) ?? null;
  const openTrades = (ws["trades.open"] as Trade[] | undefined) ?? [];

  const [equityHistory, setEquityHistory] = useState<
    { t: number; equity: number }[]
  >([]);

  useEffect(() => {
    if (!account) return;
    setEquityHistory((prev) => {
      const next = [...prev, { t: Date.now(), equity: account.equity }];
      return next.slice(-240);
    });
  }, [account?.equity]);

  const profitTone =
    (account?.profit ?? 0) > 0
      ? "good"
      : (account?.profit ?? 0) < 0
        ? "bad"
        : "neutral";

  return (
    <Shell>
      <header className="mb-6 flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Dashboard</h1>
          <p className="text-sm text-slate-400">
            Live account, strategies and KI status.
          </p>
        </div>
        <div className="text-right text-xs text-slate-400">
          <div>Mode: <span className="text-jarvis-accent">{(status as any)?.mt5_mode ?? "—"}</span></div>
          <div>Connected: {(status as any)?.connected ? "yes" : "no"}</div>
        </div>
      </header>

      <div className="mb-6 grid grid-cols-2 gap-4 md:grid-cols-4">
        <Card><Stat label="Balance" value={account?.balance?.toFixed(2) ?? "—"} unit={account?.currency} /></Card>
        <Card><Stat label="Equity" value={account?.equity?.toFixed(2) ?? "—"} unit={account?.currency} /></Card>
        <Card><Stat label="Margin" value={account?.margin?.toFixed(2) ?? "—"} /></Card>
        <Card><Stat label="Floating P/L" value={(account?.profit ?? 0).toFixed(2)} tone={profitTone} /></Card>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card title="Equity curve" className="lg:col-span-2">
          <EquityChart data={equityHistory} />
        </Card>

        <Card title="System">
          <ul className="space-y-2 text-sm">
            <li className="flex justify-between"><span className="text-slate-400">App</span><span>{(status as any)?.app}</span></li>
            <li className="flex justify-between"><span className="text-slate-400">Env</span><span>{(status as any)?.env}</span></li>
            <li className="flex justify-between"><span className="text-slate-400">Kill switch</span>
              <span className={(status as any)?.kill_switch ? "text-jarvis-err" : "text-jarvis-ok"}>
                {(status as any)?.kill_switch ? "engaged" : "released"}
              </span>
            </li>
            <li className="flex justify-between"><span className="text-slate-400">Open trades</span><span>{openTrades.length}</span></li>
          </ul>
        </Card>
      </div>

      <Card title="Open positions" className="mt-6">
        {openTrades.length === 0 ? (
          <p className="text-sm text-slate-400">No open positions.</p>
        ) : (
          <table className="w-full text-sm">
            <thead className="text-left text-xs uppercase tracking-widest text-slate-500">
              <tr>
                <th className="py-1">Ticket</th>
                <th>Symbol</th>
                <th>Side</th>
                <th>Volume</th>
                <th>Entry</th>
                <th className="text-right">P/L</th>
              </tr>
            </thead>
            <tbody className="font-mono">
              {openTrades.map((t) => (
                <tr key={t.ticket} className="border-t border-jarvis-border/60">
                  <td className="py-2">{t.ticket}</td>
                  <td>{t.symbol}</td>
                  <td className={t.side === "BUY" ? "text-jarvis-ok" : "text-jarvis-err"}>{t.side}</td>
                  <td>{t.volume}</td>
                  <td>{t.entry_price.toFixed(5)}</td>
                  <td className={`text-right ${t.profit >= 0 ? "text-jarvis-ok" : "text-jarvis-err"}`}>
                    {t.profit.toFixed(2)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </Shell>
  );
}
