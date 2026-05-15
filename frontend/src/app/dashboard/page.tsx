"use client";

import { useEffect, useState } from "react";
import { API_BASE, WS_BASE } from "@/lib/config";

type MetricsPayload = {
  account: Record<string, unknown> | null;
  positions: unknown[];
};

export default function DashboardPage() {
  const [restSnapshot, setRestSnapshot] = useState<MetricsPayload | null>(null);
  const [live, setLive] = useState<MetricsPayload | null>(null);
  const [wsState, setWsState] = useState<"idle" | "open" | "error">("idle");

  useEffect(() => {
    const load = async () => {
      try {
        const [acc, pos] = await Promise.all([
          fetch(`${API_BASE}/api/v1/mt5/account`).then((r) => r.json()),
          fetch(`${API_BASE}/api/v1/mt5/positions`).then((r) => r.json()),
        ]);
        const account = acc.connected
          ? {
              balance: acc.balance,
              equity: acc.equity,
              margin: acc.margin,
              margin_free: acc.margin_free,
              server: acc.server,
              currency: acc.currency,
            }
          : null;
        setRestSnapshot({
          account,
          positions: pos.positions ?? [],
        });
      } catch {
        setRestSnapshot({ account: null, positions: [] });
      }
    };
    void load();
  }, []);

  useEffect(() => {
    const url = `${WS_BASE}/ws/v1/stream`;
    let ws: WebSocket;
    try {
      ws = new WebSocket(url);
    } catch {
      setWsState("error");
      return () => undefined;
    }
    ws.onopen = () => setWsState("open");
    ws.onerror = () => setWsState("error");
    ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data as string);
        if (msg.type === "metrics") {
          setLive(msg.payload as MetricsPayload);
        }
      } catch {
        /* ignore */
      }
    };
    return () => ws.close();
  }, []);

  const snapshot = live ?? restSnapshot;

  return (
    <main className="mx-auto flex max-w-6xl flex-col gap-6 px-4 py-8">
      <div>
        <h1 className="text-2xl font-semibold">Live cockpit</h1>
        <p className="text-sm text-slate-400">
          REST bootstrap plus WebSocket stream from the FastAPI control plane.
        </p>
      </div>

      <section className="grid gap-4 md:grid-cols-3">
        <MetricCard
          label="WebSocket"
          value={wsState === "open" ? "Connected" : wsState === "error" ? "Issue" : "Idle"}
        />
        <MetricCard
          label="Balance"
          value={formatMoney(snapshot?.account?.balance as number | undefined)}
        />
        <MetricCard
          label="Equity"
          value={formatMoney(snapshot?.account?.equity as number | undefined)}
        />
        <MetricCard
          label="Margin"
          value={formatMoney(snapshot?.account?.margin as number | undefined)}
        />
        <MetricCard
          label="Open positions"
          value={String(snapshot?.positions?.length ?? 0)}
        />
        <MetricCard
          label="Server"
          value={(snapshot?.account?.server as string) || "n/a"}
        />
      </section>

      <section className="rounded-lg border border-slate-800 bg-slate-900/40 p-4">
        <h2 className="text-sm font-semibold text-slate-200">Raw snapshot</h2>
        <pre className="mt-3 max-h-96 overflow-auto text-xs text-slate-300">
          {JSON.stringify(snapshot, null, 2)}
        </pre>
      </section>
    </main>
  );
}

function MetricCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900/50 p-4">
      <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-2 text-lg font-semibold">{value}</p>
    </div>
  );
}

function formatMoney(v: number | undefined) {
  if (v === undefined || v === null || Number.isNaN(v)) return "—";
  return v.toFixed(2);
}
