import { CommandConsole } from "../components/command-console";
import { StatusCard } from "../components/status-card";

const metrics = [
  { label: "Balance", value: "$10,000" },
  { label: "Equity", value: "$10,120", tone: "positive" as const },
  { label: "Margin", value: "$245" },
  { label: "Win Rate", value: "58%", tone: "positive" as const },
  { label: "Drawdown", value: "8%", tone: "negative" as const },
  { label: "Open Trades", value: "1" }
];

export default function Home() {
  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top,_rgba(34,211,238,0.14),_transparent_40%),_#050816] px-6 py-10">
      <div className="mx-auto max-w-7xl space-y-8">
        <header className="flex flex-col gap-3">
          <p className="text-sm uppercase tracking-[0.32em] text-cyan-300">JARVIS Trading OS</p>
          <h1 className="text-4xl font-semibold text-white">AI Trading Command Center</h1>
          <p className="max-w-3xl text-slate-300">
            Modular dashboard for strategy generation, risk supervision, MT5 deployment planning,
            Telegram alerts and live operator control.
          </p>
        </header>

        <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {metrics.map((metric) => (
            <StatusCard key={metric.label} label={metric.label} value={metric.value} tone={metric.tone} />
          ))}
        </section>

        <section className="grid gap-6 xl:grid-cols-[2fr_1fr]">
          <CommandConsole />

          <div className="space-y-6">
            <div className="panel p-6">
              <p className="text-sm uppercase tracking-[0.24em] text-slate-400">Risk Engine</p>
              <ul className="mt-4 space-y-3 text-sm text-slate-200">
                <li>Only one live trade is allowed at any time.</li>
                <li>Hedging is disabled to avoid simultaneous buy and sell exposure.</li>
                <li>Trades are force-closed when loss reaches 20%.</li>
              </ul>
            </div>

            <div className="panel p-6">
              <p className="text-sm uppercase tracking-[0.24em] text-slate-400">Integrations</p>
              <div className="mt-4 space-y-3 text-sm text-slate-200">
                <p>MT5 connector scaffolded</p>
                <p>Telegram event formatting scaffolded</p>
                <p>TradingView Pine template scaffolded</p>
                <p>Docker, PostgreSQL and Redis ready</p>
              </div>
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
