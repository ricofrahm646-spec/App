"use client";

import useSWR from "swr";
import { Card } from "@/components/Card";
import { Shell } from "@/components/Shell";
import { api, fetcher } from "@/lib/api";

export default function SystemPage() {
  const { data: status, mutate } = useSWR<Record<string, unknown>>(
    "/api/system/status",
    fetcher,
    { refreshInterval: 3000 },
  );

  return (
    <Shell>
      <h1 className="mb-1 text-2xl font-semibold">System</h1>
      <p className="mb-6 text-sm text-slate-400">
        Emergency controls and platform status.
      </p>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <Card title="Status">
          <pre className="overflow-x-auto rounded-lg bg-jarvis-bg p-3 text-xs">
{JSON.stringify(status, null, 2)}
          </pre>
        </Card>

        <Card title="Controls">
          <div className="flex flex-col gap-3">
            <button
              onClick={async () => {
                await api("/api/system/kill-switch", { method: "POST" });
                mutate();
              }}
              className="rounded-lg bg-jarvis-err px-4 py-2 text-sm font-semibold text-white hover:bg-red-600"
            >
              Engage kill switch (flatten everything)
            </button>

            <button
              onClick={async () => {
                await api("/api/system/resume", { method: "POST" });
                mutate();
              }}
              className="rounded-lg bg-jarvis-ok px-4 py-2 text-sm font-semibold text-slate-900 hover:bg-emerald-400"
            >
              Resume trading
            </button>

            <button
              onClick={async () => {
                await api("/api/trades/close-all", { method: "POST" });
              }}
              className="rounded-lg border border-jarvis-border px-4 py-2 text-sm hover:bg-jarvis-border/40"
            >
              Close all positions
            </button>
          </div>
        </Card>
      </div>
    </Shell>
  );
}
