"use client";

import { FormEvent, useState } from "react";

type GeneratedFile = {
  path: string;
  language: string;
  purpose: string;
};

type ChatResponse = {
  intent: string;
  summary: string;
  actions: string[];
  generated_files: GeneratedFile[];
  safety_notes: string[];
};

const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export function ChatPanel() {
  const [message, setMessage] = useState("Baue einen neuen Gold-Scalping-Bot mit Trailing Stop");
  const [response, setResponse] = useState<ChatResponse | null>(null);
  const [loading, setLoading] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    const result = await fetch(`${apiBase}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, dry_run: true })
    });
    setResponse(await result.json());
    setLoading(false);
  }

  return (
    <section className="rounded-3xl border border-jarvis-accent/20 bg-jarvis-panel p-6 shadow-2xl">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm uppercase tracking-[0.25em] text-jarvis-accent">AI Command Center</p>
          <h2 className="mt-2 text-2xl font-bold">JARVIS Chat</h2>
        </div>
        <span className="rounded-full bg-jarvis-accent/10 px-3 py-1 text-sm text-jarvis-accent">
          Safety-first
        </span>
      </div>
      <form onSubmit={submit} className="mt-6 space-y-4">
        <textarea
          className="min-h-32 w-full rounded-2xl border border-white/10 bg-black/20 p-4 text-white outline-none ring-jarvis-accent/50 focus:ring-2"
          value={message}
          onChange={(event) => setMessage(event.target.value)}
        />
        <button
          type="submit"
          disabled={loading}
          className="rounded-xl bg-jarvis-accent px-5 py-3 font-semibold text-slate-950 disabled:opacity-60"
        >
          {loading ? "JARVIS analysiert..." : "Befehl ausfuehren"}
        </button>
      </form>

      {response ? (
        <div className="mt-6 space-y-4 rounded-2xl bg-black/20 p-4">
          <p className="text-sm text-slate-400">Intent: {response.intent}</p>
          <p className="text-lg font-semibold">{response.summary}</p>
          <div>
            <p className="font-semibold text-jarvis-accent">Aktionen</p>
            <ul className="mt-2 list-disc space-y-1 pl-5 text-slate-300">
              {response.actions.map((action) => (
                <li key={action}>{action}</li>
              ))}
            </ul>
          </div>
          <div>
            <p className="font-semibold text-jarvis-accent">Generierte Dateien</p>
            <ul className="mt-2 space-y-2">
              {response.generated_files.map((file) => (
                <li key={file.path} className="rounded-xl bg-white/5 p-3 text-sm">
                  <span className="font-mono text-jarvis-accent">{file.path}</span>
                  <span className="ml-2 text-slate-400">({file.language}, {file.purpose})</span>
                </li>
              ))}
            </ul>
          </div>
          <ul className="list-disc space-y-1 pl-5 text-sm text-jarvis-warning">
            {response.safety_notes.map((note) => (
              <li key={note}>{note}</li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  );
}
