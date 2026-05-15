"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import clsx from "clsx";

const nav = [
  { href: "/", label: "Dashboard" },
  { href: "/chat", label: "AI Chat" },
  { href: "/strategies", label: "Strategies" },
  { href: "/backtest", label: "Backtest" },
  { href: "/mql5", label: "MQL5" },
  { href: "/system", label: "System" },
];

export function Sidebar() {
  const path = usePathname();
  return (
    <aside className="w-56 shrink-0 border-r border-jarvis-border bg-jarvis-surface/60 p-4">
      <div className="mb-8 flex items-center gap-2">
        <div className="h-8 w-8 rounded-lg bg-gradient-to-br from-jarvis-accent to-cyan-500" />
        <div>
          <div className="text-lg font-bold tracking-tight">JARVIS</div>
          <div className="text-xs text-slate-500">AI Trading OS</div>
        </div>
      </div>
      <nav className="flex flex-col gap-1">
        {nav.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={clsx(
              "rounded-lg px-3 py-2 text-sm transition-colors",
              path === item.href
                ? "bg-jarvis-accent/10 text-jarvis-accent"
                : "text-slate-300 hover:bg-jarvis-border/40",
            )}
          >
            {item.label}
          </Link>
        ))}
      </nav>
      <div className="mt-8 rounded-lg border border-jarvis-border p-3 text-xs text-slate-400">
        Trade carefully. No system can guarantee profits.
      </div>
    </aside>
  );
}
