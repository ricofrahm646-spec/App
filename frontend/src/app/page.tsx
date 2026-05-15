import Link from "next/link";

export default function Home() {
  return (
    <main className="min-h-screen bg-slate-950 text-slate-50 flex flex-col items-center justify-center gap-8 p-8">
      <div className="text-center space-y-3 max-w-lg">
        <p className="text-xs uppercase tracking-[0.3em] text-emerald-400">
          JARVIS
        </p>
        <h1 className="text-3xl font-semibold">Trading Operating System</h1>
        <p className="text-sm text-slate-400">
          Modular control plane for research, execution, and monitoring. No
          performance guarantees — risk first.
        </p>
      </div>
      <div className="flex gap-4">
        <Link
          href="/dashboard"
          className="rounded-md bg-emerald-500 px-5 py-2 text-sm font-medium text-slate-950 hover:bg-emerald-400"
        >
          Open dashboard
        </Link>
        <Link
          href="/chat"
          className="rounded-md border border-slate-700 px-5 py-2 text-sm hover:border-emerald-400"
        >
          Open JARVIS chat
        </Link>
      </div>
    </main>
  );
}
