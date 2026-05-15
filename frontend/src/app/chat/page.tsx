"use client";

import { FormEvent, useState } from "react";
import { API_BASE } from "@/lib/config";

type ChatResponse = {
  reply: string;
  actions: { kind: string; payload: Record<string, unknown> }[];
};

export default function ChatPage() {
  const [input, setInput] = useState(
    "Baue einen neuen Gold-Scalping-Bot als EA-Grundgerüst.",
  );
  const [history, setHistory] = useState<{ role: "user" | "jarvis"; text: string }[]>(
    [],
  );
  const [loading, setLoading] = useState(false);

  const send = async (event: FormEvent) => {
    event.preventDefault();
    if (!input.trim()) return;
    const userText = input.trim();
    setInput("");
    setHistory((h) => [...h, { role: "user", text: userText }]);
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/v1/chat/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: userText }),
      });
      const data = (await res.json()) as ChatResponse;
      setHistory((h) => [...h, { role: "jarvis", text: data.reply }]);
    } catch {
      setHistory((h) => [
        ...h,
        { role: "jarvis", text: "Konnte den Control-Plane-Server nicht erreichen." },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="mx-auto flex max-w-4xl flex-col gap-4 px-4 py-8">
      <div>
        <h1 className="text-2xl font-semibold">JARVIS Chat</h1>
        <p className="text-sm text-slate-400">
          Steuere Generatoren für MQL5, Python-Module und spätere KI-Workflows.
        </p>
      </div>

      <div className="flex h-[480px] flex-col rounded-lg border border-slate-800 bg-slate-900/40">
        <div className="flex-1 space-y-3 overflow-y-auto p-4 text-sm">
          {history.length === 0 && (
            <p className="text-slate-500">
              Stelle eine konkrete Aufgabe, z. B. EA für XAUUSD oder News-Filter
              in Python.
            </p>
          )}
          {history.map((m, idx) => (
            <div
              key={idx}
              className={`max-w-[85%] rounded-lg px-3 py-2 ${
                m.role === "user"
                  ? "ml-auto bg-emerald-600/20 text-emerald-50"
                  : "bg-slate-800 text-slate-100"
              }`}
            >
              {m.text}
            </div>
          ))}
        </div>
        <form
          onSubmit={send}
          className="border-t border-slate-800 p-3 flex gap-2 bg-slate-950/60"
        >
          <input
            className="flex-1 rounded-md border border-slate-800 bg-slate-950 px-3 py-2 text-sm outline-none focus:border-emerald-500"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Befehl eingeben…"
          />
          <button
            type="submit"
            disabled={loading}
            className="rounded-md bg-emerald-500 px-4 py-2 text-sm font-medium text-slate-950 disabled:opacity-50"
          >
            {loading ? "…" : "Senden"}
          </button>
        </form>
      </div>
    </main>
  );
}
