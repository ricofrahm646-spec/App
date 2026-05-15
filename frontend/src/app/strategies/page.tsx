"use client";

import useSWR from "swr";
import { Card } from "@/components/Card";
import { Shell } from "@/components/Shell";
import { api, fetcher } from "@/lib/api";

type Strategy = {
  id: number;
  name: string;
  kind: string;
  symbol: string;
  timeframe: string;
  enabled: boolean;
  score: number;
};

export default function StrategiesPage() {
  const { data: strategies, mutate } = useSWR<Strategy[]>(
    "/api/strategies",
    fetcher,
  );
  const { data: kinds } = useSWR<string[]>("/api/strategies/kinds", fetcher);

  const toggle = async (id: number) => {
    await api(`/api/strategies/${id}/toggle`, { method: "POST" });
    mutate();
  };

  return (
    <Shell>
      <h1 className="mb-1 text-2xl font-semibold">Strategies</h1>
      <p className="mb-6 text-sm text-slate-400">
        Built-in kinds: {kinds?.join(", ") ?? "—"}
      </p>
      <Card title="Registered strategies">
        {!strategies || strategies.length === 0 ? (
          <p className="text-sm text-slate-400">
            No strategies registered yet. Use the chat to build one.
          </p>
        ) : (
          <table className="w-full text-sm">
            <thead className="text-left text-xs uppercase tracking-widest text-slate-500">
              <tr>
                <th className="py-1">Name</th>
                <th>Kind</th>
                <th>Symbol</th>
                <th>Timeframe</th>
                <th>Score</th>
                <th>Enabled</th>
              </tr>
            </thead>
            <tbody>
              {strategies.map((s) => (
                <tr key={s.id} className="border-t border-jarvis-border/60">
                  <td className="py-2">{s.name}</td>
                  <td className="text-slate-400">{s.kind}</td>
                  <td className="font-mono">{s.symbol}</td>
                  <td className="font-mono">{s.timeframe}</td>
                  <td className="font-mono">{s.score.toFixed(2)}</td>
                  <td>
                    <button
                      onClick={() => toggle(s.id)}
                      className={`rounded-full px-3 py-0.5 text-xs ${
                        s.enabled
                          ? "bg-jarvis-ok/20 text-jarvis-ok"
                          : "bg-jarvis-err/20 text-jarvis-err"
                      }`}
                    >
                      {s.enabled ? "on" : "off"}
                    </button>
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
