"use client";

import { useEffect, useState } from "react";
import { fetchDashboardMetrics } from "@/lib/api";
import type { DashboardMetric } from "@/lib/types";

export function Dashboard() {
  const [metrics, setMetrics] = useState<DashboardMetric[]>([]);

  useEffect(() => {
    void fetchDashboardMetrics().then(setMetrics);
  }, []);

  return (
    <section className="space-y-4">
      <h2 className="text-xl font-semibold">Live Trading Dashboard</h2>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {metrics.map((metric) => (
          <article key={metric.label} className="rounded-xl bg-panel p-4 shadow">
            <p className="text-sm text-zinc-400">{metric.label}</p>
            <p className="mt-2 text-2xl font-semibold">{metric.value}</p>
            {metric.trend ? (
              <p className="mt-1 text-xs text-emerald-400">{metric.trend}</p>
            ) : null}
          </article>
        ))}
      </div>
    </section>
  );
}
