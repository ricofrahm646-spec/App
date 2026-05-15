"use client";

import { useState } from "react";

import { runChatCommand, type ChatCommandResponse } from "@/lib/api";

const starterPrompts = [
  "Baue einen neuen Gold-Scalping-Bot",
  "Erstelle einen ICT-Bot",
  "Baue einen News-Filter",
  "Füge Trailing Stop hinzu",
];

export function ChatPanel() {
  const [message, setMessage] = useState(starterPrompts[0]);
  const [response, setResponse] = useState<ChatCommandResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(nextMessage: string) {
    setIsLoading(true);
    setError(null);

    try {
      const result = await runChatCommand(nextMessage);
      setResponse(result);
    } catch (submitError) {
      setError(
        submitError instanceof Error
          ? submitError.message
          : "JARVIS could not process the request.",
      );
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <section className="rounded-3xl border border-cyan-500/20 bg-slate-950/80 p-6 shadow-2xl shadow-cyan-950/30">
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="text-sm uppercase tracking-[0.2em] text-cyan-300">
            JARVIS Command Center
          </p>
          <h2 className="mt-2 text-2xl font-semibold text-white">
            AI chat interface
          </h2>
        </div>
        <span className="rounded-full bg-cyan-500/10 px-3 py-1 text-xs font-medium text-cyan-200 ring-1 ring-cyan-500/30">
          Generate modules
        </span>
      </div>

      <div className="mt-5 flex flex-wrap gap-2">
        {starterPrompts.map((prompt) => (
          <button
            key={prompt}
            type="button"
            onClick={() => {
              setMessage(prompt);
              void handleSubmit(prompt);
            }}
            className="rounded-full border border-white/10 bg-white/5 px-3 py-2 text-sm text-slate-200 transition hover:bg-white/10"
          >
            {prompt}
          </button>
        ))}
      </div>

      <form
        className="mt-5 space-y-4"
        onSubmit={(event) => {
          event.preventDefault();
          void handleSubmit(message);
        }}
      >
        <textarea
          value={message}
          onChange={(event) => setMessage(event.target.value)}
          className="min-h-32 w-full rounded-2xl border border-white/10 bg-black/30 px-4 py-3 text-sm text-white outline-none ring-0 placeholder:text-slate-500 focus:border-cyan-500/50"
          placeholder="Describe the trading bot, strategy improvement, or integration task."
        />
        <button
          type="submit"
          disabled={isLoading}
          className="rounded-full bg-cyan-400 px-5 py-3 text-sm font-semibold text-slate-950 transition hover:bg-cyan-300 disabled:cursor-not-allowed disabled:bg-cyan-800"
        >
          {isLoading ? "Generating..." : "Run JARVIS command"}
        </button>
      </form>

      {error ? (
        <div className="mt-5 rounded-2xl border border-rose-500/20 bg-rose-500/10 p-4 text-sm text-rose-200">
          {error}
        </div>
      ) : null}

      {response ? (
        <div className="mt-6 space-y-5">
          <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
            <p className="text-xs uppercase tracking-[0.2em] text-slate-400">
              Response
            </p>
            <h3 className="mt-2 text-xl font-semibold text-white">
              {response.plan.title}
            </h3>
            <p className="mt-2 text-sm text-slate-300">
              {response.acknowledgement}
            </p>
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
              <p className="text-sm font-semibold text-white">Generated files</p>
              <ul className="mt-3 space-y-2 text-sm text-slate-300">
                {response.created_files.map((file) => (
                  <li key={file} className="rounded-xl bg-white/5 px-3 py-2">
                    {file}
                  </li>
                ))}
              </ul>
            </div>

            <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
              <p className="text-sm font-semibold text-white">Risk notes</p>
              <ul className="mt-3 space-y-2 text-sm text-slate-300">
                {response.plan.risk_notes.map((note) => (
                  <li key={note}>- {note}</li>
                ))}
              </ul>
            </div>
          </div>

          <div className="rounded-2xl border border-white/10 bg-black/20 p-4">
            <p className="text-sm font-semibold text-white">Execution plan</p>
            <ol className="mt-3 space-y-2 text-sm text-slate-300">
              {response.plan.actions.map((action) => (
                <li key={action}>
                  <span className="mr-2 text-cyan-300">•</span>
                  {action}
                </li>
              ))}
            </ol>
          </div>
        </div>
      ) : null}
    </section>
  );
}
