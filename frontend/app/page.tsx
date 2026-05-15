import { JarvisChat } from "../components/JarvisChat";
import { MetricCard } from "../components/MetricCard";

type Snapshot = {
  balance: number;
  equity: number;
  margin: number;
  winrate: number;
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  profit_factor: number;
  drawdown: number;
  ai_status: string;
  strategy_status: string;
  live_market_analysis: Record<string, string>;
};

async function getSnapshot(): Promise<Snapshot> {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  try {
    const response = await fetch(`${apiUrl}/dashboard/snapshot`, { cache: "no-store" });
    return (await response.json()) as Snapshot;
  } catch {
    return {
      balance: 0,
      equity: 0,
      margin: 0,
      winrate: 0,
      total_trades: 0,
      winning_trades: 0,
      losing_trades: 0,
      profit_factor: 0,
      drawdown: 0,
      ai_status: "offline",
      strategy_status: "backend_unavailable",
      live_market_analysis: { regime: "unknown" }
    };
  }
}

export default async function DashboardPage() {
  const snapshot = await getSnapshot();

  return (
    <main className="min-h-screen px-6 py-8">
      <div className="mx-auto max-w-7xl">
        <header className="mb-8 flex flex-col justify-between gap-4 md:flex-row md:items-end">
          <div>
            <p className="text-sm uppercase tracking-[0.4em] text-sky-300">JARVIS</p>
            <h1 className="text-4xl font-bold md:text-6xl">AI Trading Operating System</h1>
            <p className="mt-3 max-w-3xl text-slate-300">
              Modular strategy generation, MT5 automation, risk control, backtesting,
              TradingView webhooks and Telegram alerts without fabricated performance claims.
            </p>
          </div>
          <div className="rounded-2xl border border-slate-700 bg-slate-900/70 p-4 text-sm text-slate-300">
            <p>AI Status: {snapshot.ai_status}</p>
            <p>Strategy: {snapshot.strategy_status}</p>
          </div>
        </header>

        <section className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <MetricCard label="Balance" value={`$${snapshot.balance.toLocaleString()}`} />
          <MetricCard label="Equity" value={`$${snapshot.equity.toLocaleString()}`} />
          <MetricCard label="Margin" value={`$${snapshot.margin.toLocaleString()}`} />
          <MetricCard label="Drawdown" value={`${snapshot.drawdown}%`} tone="danger" />
          <MetricCard label="Winrate" value={`${snapshot.winrate}%`} />
          <MetricCard label="Total Trades" value={snapshot.total_trades} />
          <MetricCard label="Profit Factor" value={snapshot.profit_factor} tone="success" />
          <MetricCard
            label="Market Regime"
            value={snapshot.live_market_analysis.regime ?? "unknown"}
          />
        </section>

        <div className="mt-8 grid gap-6 lg:grid-cols-[1.4fr_0.8fr]">
          <JarvisChat />
          <aside className="rounded-3xl border border-slate-700 bg-slate-900/70 p-5">
            <h2 className="text-2xl font-semibold">Risk Guardrails</h2>
            <ul className="mt-4 space-y-3 text-sm text-slate-300">
              <li>Maximal ein offener Trade gleichzeitig.</li>
              <li>Keine gleichzeitigen Buy- und Sell-Positionen.</li>
              <li>Lotgröße wird aus Equity, Risiko und Stop-Distanz berechnet.</li>
              <li>Notfall-Schließung ab 20% Verlustschwelle.</li>
              <li>Backtests müssen Spread, Slippage und Walk-Forward-Prüfung enthalten.</li>
            </ul>
          </aside>
        </div>
      </div>
    </main>
  );
}
