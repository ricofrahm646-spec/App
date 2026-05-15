"use client";

import { useState } from "react";
import useSWR from "swr";
import { Card } from "@/components/Card";
import { Shell } from "@/components/Shell";
import { api, fetcher } from "@/lib/api";

type Generated = {
  name: string;
  path: string;
  size: number;
  modified: string;
};

export default function Mql5Page() {
  const { data: files, mutate } = useSWR<Generated[]>(
    "/api/mql5/list",
    fetcher,
    { refreshInterval: 5000 },
  );

  const [form, setForm] = useState({
    name: "MyGoldScalper",
    symbol: "XAUUSD",
    timeframe: "M5",
    strategy_kind: "scalping",
  });

  const generate = async () => {
    await api("/api/mql5/generate-ea", {
      method: "POST",
      body: JSON.stringify(form),
    });
    mutate();
  };

  const install = async (path: string) => {
    await api("/api/mql5/install", {
      method: "POST",
      body: JSON.stringify({ file_path: path, kind: "ea" }),
    });
  };

  return (
    <Shell>
      <h1 className="mb-1 text-2xl font-semibold">MQL5</h1>
      <p className="mb-6 text-sm text-slate-400">
        Generate Expert Advisors and indicators, then install them directly into
        the MetaTrader 5 data folder.
      </p>

      <Card title="Generate EA" className="mb-4">
        <div className="grid grid-cols-2 gap-3 md:grid-cols-5">
          {(["name", "symbol", "timeframe", "strategy_kind"] as const).map(
            (k) => (
              <label key={k} className="text-xs uppercase tracking-widest text-slate-400">
                {k}
                <input
                  value={(form as any)[k]}
                  onChange={(e) => setForm({ ...form, [k]: e.target.value })}
                  className="mt-1 w-full rounded-lg border border-jarvis-border bg-jarvis-bg px-3 py-2 text-sm font-mono text-slate-100"
                />
              </label>
            ),
          )}
          <button
            onClick={generate}
            className="mt-5 rounded-lg bg-jarvis-accent px-4 py-2 text-sm font-semibold text-slate-900 hover:bg-cyan-300"
          >
            Generate
          </button>
        </div>
      </Card>

      <Card title="Generated files">
        {!files || files.length === 0 ? (
          <p className="text-sm text-slate-400">
            No files yet. Generate one above or via the chat.
          </p>
        ) : (
          <table className="w-full text-sm">
            <thead className="text-left text-xs uppercase tracking-widest text-slate-500">
              <tr>
                <th className="py-1">Name</th>
                <th>Size</th>
                <th>Modified</th>
                <th />
              </tr>
            </thead>
            <tbody className="font-mono">
              {files.map((f) => (
                <tr key={f.path} className="border-t border-jarvis-border/60">
                  <td className="py-2">{f.name}.mq5</td>
                  <td>{f.size} B</td>
                  <td>{f.modified}</td>
                  <td className="text-right">
                    <button
                      onClick={() => install(f.path)}
                      className="rounded-full bg-jarvis-accent/20 px-3 py-0.5 text-xs text-jarvis-accent hover:bg-jarvis-accent/30"
                    >
                      Install
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
