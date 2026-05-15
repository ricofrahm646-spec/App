'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import { api, type ChatMessage } from '@/lib/api';
import { cn } from '@/lib/utils';
import { Send, Bot, User, Loader2, Sparkles } from 'lucide-react';
import { format } from 'date-fns';

const SUGGESTIONS = [
  'Baue einen Gold-Scalping-Bot',
  'Optimiere die Winrate',
  'Erstelle einen ICT-Bot',
  'Baue einen Telegram-Signal-Bot',
  'Optimiere den Drawdown',
];

export default function ChatInterface() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [historyLoaded, setHistoryLoaded] = useState(false);
  const messagesEnd = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const scrollToBottom = useCallback(() => {
    messagesEnd.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  useEffect(() => {
    async function loadHistory() {
      try {
        const history = await api.getChatHistory();
        setMessages(history);
      } catch {
        /* API not available */
      } finally {
        setHistoryLoaded(true);
      }
    }
    loadHistory();
  }, []);

  const sendMessage = async (content: string) => {
    if (!content.trim() || loading) return;

    const userMessage: ChatMessage = { role: 'user', content: content.trim(), created_at: new Date().toISOString() };
    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    try {
      const response = await api.sendChatMessage(content.trim());
      setMessages((prev) => [...prev, response]);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: 'Sorry, I could not process your request. Please check the backend connection.',
          created_at: new Date().toISOString(),
        },
      ]);
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  };

  return (
    <div className="flex h-full flex-col">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-6">
        {!historyLoaded ? (
          <div className="flex h-full items-center justify-center">
            <Loader2 className="h-6 w-6 animate-spin text-slate-500" />
          </div>
        ) : messages.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center text-center">
            <div className="mb-4 rounded-full bg-blue-500/10 p-4">
              <Sparkles className="h-8 w-8 text-blue-400" />
            </div>
            <h2 className="mb-2 text-xl font-semibold text-white">JARVIS AI Assistant</h2>
            <p className="mb-8 max-w-md text-sm text-slate-400">
              I can help you build trading bots, analyze strategies, optimize performance, and manage your trading operations.
            </p>
            <div className="flex flex-wrap justify-center gap-2">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  onClick={() => sendMessage(s)}
                  className="rounded-full border border-slate-700 bg-slate-800/50 px-4 py-2 text-sm text-slate-300 transition-all hover:border-blue-500/50 hover:bg-blue-500/10 hover:text-blue-300"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="mx-auto max-w-3xl space-y-4">
            {messages.map((msg, i) => (
              <div
                key={msg.id ?? i}
                className={cn('flex gap-3', msg.role === 'user' ? 'justify-end' : 'justify-start')}
              >
                {msg.role === 'assistant' && (
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-blue-500/20">
                    <Bot className="h-4 w-4 text-blue-400" />
                  </div>
                )}
                <div
                  className={cn(
                    'max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-relaxed',
                    msg.role === 'user'
                      ? 'bg-blue-600 text-white'
                      : 'border border-slate-700/50 bg-slate-800/80 text-slate-200'
                  )}
                >
                  <MessageContent content={msg.content} />
                  {msg.created_at && (
                    <p
                      className={cn(
                        'mt-1 text-[10px]',
                        msg.role === 'user' ? 'text-blue-200' : 'text-slate-500'
                      )}
                    >
                      {format(new Date(msg.created_at), 'HH:mm')}
                    </p>
                  )}
                </div>
                {msg.role === 'user' && (
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-slate-600">
                    <User className="h-4 w-4 text-slate-300" />
                  </div>
                )}
              </div>
            ))}
            {loading && (
              <div className="flex gap-3">
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-blue-500/20">
                  <Bot className="h-4 w-4 text-blue-400" />
                </div>
                <div className="rounded-2xl border border-slate-700/50 bg-slate-800/80 px-4 py-3">
                  <div className="flex items-center gap-1">
                    <div className="h-2 w-2 animate-bounce rounded-full bg-blue-400 [animation-delay:0ms]" />
                    <div className="h-2 w-2 animate-bounce rounded-full bg-blue-400 [animation-delay:150ms]" />
                    <div className="h-2 w-2 animate-bounce rounded-full bg-blue-400 [animation-delay:300ms]" />
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEnd} />
          </div>
        )}
      </div>

      {/* Suggestion chips when there are messages */}
      {messages.length > 0 && !loading && (
        <div className="flex gap-2 overflow-x-auto border-t border-slate-700/30 px-4 py-2">
          {SUGGESTIONS.map((s) => (
            <button
              key={s}
              onClick={() => sendMessage(s)}
              className="shrink-0 rounded-full border border-slate-700/50 bg-slate-800/50 px-3 py-1 text-xs text-slate-400 transition-colors hover:border-blue-500/50 hover:text-blue-300"
            >
              {s}
            </button>
          ))}
        </div>
      )}

      {/* Input */}
      <div className="border-t border-slate-700/50 bg-slate-900/50 p-4">
        <div className="mx-auto flex max-w-3xl items-end gap-2">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask JARVIS anything..."
            rows={1}
            className="flex-1 resize-none rounded-xl border border-slate-700 bg-slate-800 px-4 py-3 text-sm text-white placeholder-slate-500 outline-none transition-colors focus:border-blue-500"
          />
          <button
            onClick={() => sendMessage(input)}
            disabled={!input.trim() || loading}
            className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-blue-600 text-white transition-colors hover:bg-blue-500 disabled:opacity-40 disabled:hover:bg-blue-600"
          >
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
          </button>
        </div>
      </div>
    </div>
  );
}

function MessageContent({ content }: { content: string }) {
  const parts = content.split(/(```[\s\S]*?```)/g);
  return (
    <>
      {parts.map((part, i) => {
        if (part.startsWith('```') && part.endsWith('```')) {
          const lines = part.slice(3, -3).split('\n');
          const lang = lines[0]?.trim() || '';
          const code = (lang ? lines.slice(1) : lines).join('\n');
          return (
            <div key={i} className="my-2 overflow-x-auto rounded-lg bg-slate-900 p-3">
              {lang && (
                <div className="mb-2 text-[10px] font-medium uppercase tracking-wider text-slate-500">
                  {lang}
                </div>
              )}
              <pre className="text-xs text-slate-300">
                <code>{code}</code>
              </pre>
            </div>
          );
        }
        return <span key={i}>{part}</span>;
      })}
    </>
  );
}
