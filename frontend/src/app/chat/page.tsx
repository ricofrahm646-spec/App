"use client";

import { useEffect, useRef, useState } from "react";
import { Card } from "@/components/Card";
import { Shell } from "@/components/Shell";
import { api } from "@/lib/api";

type Turn = {
  role: "user" | "assistant" | "system";
  content: string;
  intent?: string | null;
  meta?: Record<string, unknown>;
};

const SUGGESTIONS = [
  "Build a new Gold-Scalping bot",
  "Create an ICT bot for EURUSD M5",
  "Add a trailing stop",
  "Improve drawdown of the trend follower",
  "Build a Telegram signal bot",
  "Generate an RSI divergence indicator",
];

export default function ChatPage() {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState("");
  const [pending, setPending] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api<Turn[]>("/api/chat/history").then(setTurns).catch(() => undefined);
  }, []);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [turns]);

  const send = async (text?: string) => {
    const message = (text ?? input).trim();
    if (!message || pending) return;
    setPending(true);
    setTurns((t) => [...t, { role: "user", content: message }]);
    setInput("");
    try {
      const resp = await api<Turn>("/api/chat/send", {
        method: "POST",
        body: JSON.stringify({ message }),
      });
      setTurns((t) => [...t, resp]);
    } catch (err) {
      setTurns((t) => [
        ...t,
        { role: "system", content: `Error: ${(err as Error).message}` },
      ]);
    } finally {
      setPending(false);
    }
  };

  return (
    <Shell>
      <header className="mb-4">
        <h1 className="text-2xl font-semibold">AI Chat</h1>
        <p className="text-sm text-slate-400">
          Drive JARVIS in natural language. Strategies, indicators, and EAs are
          generated on demand.
        </p>
      </header>

      <Card className="flex h-[calc(100vh-220px)] flex-col">
        <div className="flex-1 space-y-3 overflow-y-auto pr-2 scrollbar-thin">
          {turns.length === 0 && (
            <div className="rounded-lg border border-dashed border-jarvis-border p-4 text-sm text-slate-400">
              Try one of the suggestions below or describe a new strategy.
            </div>
          )}
          {turns.map((t, i) => (
            <div
              key={i}
              className={`max-w-3xl whitespace-pre-wrap rounded-2xl px-4 py-2 text-sm leading-relaxed ${
                t.role === "user"
                  ? "ml-auto bg-jarvis-accent/10 text-cyan-100"
                  : "bg-jarvis-border/40 text-slate-100"
              }`}
            >
              {t.intent && (
                <div className="mb-1 font-mono text-[10px] uppercase tracking-widest text-slate-500">
                  intent: {t.intent}
                </div>
              )}
              {t.content}
            </div>
          ))}
          <div ref={endRef} />
        </div>

        <div className="mt-4 flex flex-wrap gap-2">
          {SUGGESTIONS.map((s) => (
            <button
              key={s}
              onClick={() => send(s)}
              className="rounded-full border border-jarvis-border px-3 py-1 text-xs text-slate-300 hover:bg-jarvis-border/40"
            >
              {s}
            </button>
          ))}
        </div>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            send();
          }}
          className="mt-3 flex gap-2"
        >
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Tell JARVIS what to build…"
            className="flex-1 rounded-xl border border-jarvis-border bg-jarvis-bg px-4 py-2 text-sm outline-none focus:border-jarvis-accent"
          />
          <button
            type="submit"
            disabled={pending}
            className="rounded-xl bg-jarvis-accent px-4 py-2 text-sm font-semibold text-slate-900 hover:bg-cyan-300 disabled:opacity-50"
          >
            {pending ? "…" : "Send"}
          </button>
        </form>
      </Card>
    </Shell>
  );
}
