import { DashboardMetrics } from "@/lib/types";

const labels: Array<keyof DashboardMetrics> = [
  "balance",
  "equity",
  "margin",
  "winrate",
  "totalTrades",
  "winningTrades",
  "losingTrades",
  "profitFactor",
  "drawdown",
  "aiStatus",
  "strategyStatus"
];

export function Dashboard({ metrics }: { metrics: DashboardMetrics }) {
  return (
    <section className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
      {labels.map((key) => (
        <div className="metric-card" key={key}>
          <p className="text-xs uppercase text-slate-400">{key}</p>
          <p className="mt-2 text-2xl font-semibold">{String(metrics[key])}</p>
        </div>
      ))}
    </section>
  );
}
