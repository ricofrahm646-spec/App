import { ChatPanel } from "@/components/chat-panel";
import { Dashboard } from "@/components/dashboard";
import { DashboardMetrics } from "@/lib/types";

const defaultMetrics: DashboardMetrics = {
  balance: 10000,
  equity: 9850,
  margin: 2300,
  winrate: 0.58,
  totalTrades: 145,
  winningTrades: 84,
  losingTrades: 61,
  profitFactor: 1.42,
  drawdown: 0.11,
  aiStatus: "online",
  strategyStatus: "adaptive"
};

export default function HomePage() {
  return (
    <main className="mx-auto flex min-h-screen max-w-7xl flex-col gap-6 p-6">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">JARVIS Trading OS</h1>
          <p className="text-sm text-slate-400">Operational dashboard and AI control interface</p>
        </div>
      </header>

      <Dashboard metrics={defaultMetrics} />
      <ChatPanel />
    </main>
  );
}
