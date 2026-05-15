"use client";

import { useState } from "react";

const suggestions = [
  "Baue einen neuen Gold-Scalping-Bot",
  "Erstelle einen ICT-Bot",
  "Optimiere den Drawdown",
  "Füge Trailing Stop hinzu",
  "Baue einen Telegram-Signal-Bot"
];

type CommandResult = {
  summary: string;
  warnings: string[];
};

export function CommandConsole() {
  const [prompt, setPrompt] = useState(suggestions[0]);
  const [result, setResult] = useState<CommandResult | null>(null);
  const [loading, setLoading] = useState(false);

  async function submitCommand() {
    setLoading(true);

    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000"}/api/v1/chat/command`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify({ prompt })
        }
      );

      if (!response.ok) {
        throw new Error("Backend request failed");
      }

      const data = (await response.json()) as CommandResult;
      setResult(data);
    } catch {
      setResult({
        summary:
          "The backend is not reachable yet. The dashboard shell is ready for live API integration.",
        warnings: ["Configure NEXT_PUBLIC_API_BASE_URL and start the FastAPI backend."]
      });
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="panel p-6">
      <div className="flex flex-col gap-3">
        <p className="text-sm uppercase tracking-[0.24em] text-slate-400">Operator Console</p>
        <textarea
          className="min-h-32 rounded-xl border border-[#1f2937] bg-slate-950/60 p-4 text-sm outline-none focus:border-cyan-400"
          value={prompt}
          onChange={(event) => setPrompt(event.target.value)}
        />
        <div className="flex flex-wrap gap-2">
          {suggestions.map((entry) => (
            <button
              key={entry}
              type="button"
              className="rounded-full border border-[#1f2937] px-3 py-1 text-xs text-slate-300 transition hover:border-cyan-400 hover:text-white"
              onClick={() => setPrompt(entry)}
            >
              {entry}
            </button>
          ))}
        </div>
        <button
          type="button"
          className="w-fit rounded-xl bg-cyan-300 px-4 py-2 text-sm font-semibold text-slate-950 disabled:cursor-not-allowed disabled:opacity-60"
          onClick={submitCommand}
          disabled={loading}
        >
          {loading ? "Processing..." : "Run JARVIS Command"}
        </button>
      </div>

      {result ? (
        <div className="mt-6 space-y-3 rounded-xl border border-[#1f2937] bg-slate-950/60 p-4">
          <p className="text-sm font-medium text-white">{result.summary}</p>
          {result.warnings.map((warning) => (
            <p key={warning} className="text-sm text-amber-300">
              {warning}
            </p>
          ))}
        </div>
      ) : null}
    </div>
  );
}
