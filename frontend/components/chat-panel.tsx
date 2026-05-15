"use client";

import { FormEvent, useState } from "react";
import { sendChatMessage } from "@/lib/api";
import type { ChatResponse } from "@/lib/types";

export function ChatPanel() {
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState<ChatResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const result = await sendChatMessage(message);
      setResponse(result);
    } catch {
      setError("Chat Anfrage konnte nicht verarbeitet werden.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="rounded-xl bg-panel p-4 shadow">
      <h2 className="text-xl font-semibold">JARVIS KI-Chat</h2>
      <form onSubmit={onSubmit} className="mt-4 flex flex-col gap-3">
        <textarea
          value={message}
          onChange={(event) => setMessage(event.target.value)}
          className="min-h-24 rounded-md border border-zinc-700 bg-zinc-900 p-3"
          placeholder='z.B. "Baue einen neuen Gold-Scalping-Bot"'
          required
        />
        <button
          type="submit"
          disabled={loading}
          className="rounded-md bg-accent px-4 py-2 font-medium disabled:opacity-50"
        >
          {loading ? "Analysiere..." : "Ausfuehren"}
        </button>
      </form>

      {error ? <p className="mt-3 text-sm text-red-400">{error}</p> : null}

      {response ? (
        <div className="mt-4 space-y-2 text-sm">
          <p className="font-medium">{response.summary}</p>
          <ul className="list-disc space-y-1 pl-5 text-zinc-300">
            {response.actions.map((action) => (
              <li key={`${action.action}-${action.target_module}`}>
                <span className="font-semibold">{action.target_module}</span>:{" "}
                {action.description}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  );
}
