"use client";

import { FormEvent, useState } from "react";

type ChatResponse = {
  answer: string;
  intent: string;
  generated_files: Array<{ path: string; purpose: string }>;
  written_files?: string[];
};

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export function JarvisChat() {
  const [message, setMessage] = useState("Baue einen neuen Gold-Scalping-Bot");
  const [responses, setResponses] = useState<ChatResponse[]>([]);
  const [loading, setLoading] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    const response = await fetch(`${apiUrl}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message })
    });
    const payload = (await response.json()) as ChatResponse;
    setResponses((current) => [payload, ...current]);
    setLoading(false);
  }

  return (
    <section className="rounded-3xl border border-sky-500/30 bg-slate-950/80 p-5 shadow-2xl">
      <div className="mb-4">
        <p className="text-sm uppercase tracking-[0.3em] text-sky-300">AI Operator</p>
        <h2 className="text-2xl font-semibold">JARVIS Chat Interface</h2>
      </div>
      <form onSubmit={submit} className="flex flex-col gap-3 md:flex-row">
        <input
          className="min-h-12 flex-1 rounded-xl border border-slate-700 bg-slate-900 px-4 text-slate-100 outline-none focus:border-sky-400"
          value={message}
          onChange={(event) => setMessage(event.target.value)}
          placeholder="Erstelle einen ICT-Bot mit News-Filter"
        />
        <button
          className="rounded-xl bg-sky-400 px-5 py-3 font-semibold text-slate-950 transition hover:bg-sky-300 disabled:opacity-60"
          disabled={loading}
          type="submit"
        >
          {loading ? "Generiere..." : "Ausführen"}
        </button>
      </form>
      <div className="mt-5 space-y-4">
        {responses.map((response, index) => (
          <article key={`${response.intent}-${index}`} className="rounded-2xl bg-slate-900 p-4">
            <p className="text-slate-100">{response.answer}</p>
            <p className="mt-2 text-xs uppercase tracking-[0.2em] text-slate-500">
              Intent: {response.intent}
            </p>
            {response.generated_files.length > 0 && (
              <ul className="mt-3 space-y-1 text-sm text-sky-200">
                {response.generated_files.map((file) => (
                  <li key={file.path}>
                    {file.path} - {file.purpose}
                  </li>
                ))}
              </ul>
            )}
          </article>
        ))}
      </div>
    </section>
  );
}
