"use client";

import { useState } from "react";

import { ChatResponse } from "@/lib/types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

export function ChatPanel() {
  const [command, setCommand] = useState("");
  const [response, setResponse] = useState<ChatResponse | null>(null);
  const [loading, setLoading] = useState(false);

  const submit = async () => {
    if (!command.trim()) return;
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/chat/command`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ command, context: {} })
      });
      const data: ChatResponse = await res.json();
      setResponse(data);
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="metric-card">
      <h2 className="text-lg font-semibold">JARVIS AI Command Interface</h2>
      <p className="mt-1 text-sm text-slate-400">
        Beispiel: &quot;Baue einen neuen Gold-Scalping-Bot&quot;
      </p>
      <div className="mt-4 flex gap-2">
        <input
          className="flex-1 rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-sm"
          value={command}
          onChange={(event) => setCommand(event.target.value)}
          placeholder="Enter command..."
        />
        <button
          type="button"
          className="rounded-md bg-accent px-4 py-2 text-sm font-semibold text-black"
          onClick={submit}
          disabled={loading}
        >
          {loading ? "Working..." : "Run"}
        </button>
      </div>

      {response ? (
        <div className="mt-4 space-y-2 text-sm">
          <p className="font-semibold">{response.summary}</p>
          <ul className="list-disc pl-5 text-slate-300">
            {response.actions.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
          {response.generated_files.length ? (
            <div>
              <p className="font-semibold">Generated files:</p>
              <ul className="list-disc pl-5 text-slate-300">
                {response.generated_files.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}
