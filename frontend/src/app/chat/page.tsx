'use client';

import { useState, useRef, useEffect } from 'react';
import {
  Send,
  Bot,
  User,
  Sparkles,
  FileCode,
  TrendingUp,
  Settings,
  BarChart3,
  Loader2,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import type { ChatMessage, ChatAction } from '@/types';

const exampleCommands = [
  { label: 'Analyze EURUSD', icon: BarChart3, prompt: 'Analyze EURUSD on H1 timeframe' },
  { label: 'Create Strategy', icon: FileCode, prompt: 'Create a scalping strategy for GBPUSD' },
  { label: 'Show Performance', icon: TrendingUp, prompt: 'Show my trading performance this month' },
  { label: 'Risk Settings', icon: Settings, prompt: 'Adjust risk to 1% per trade' },
];

const initialMessages: ChatMessage[] = [
  {
    id: '1',
    role: 'assistant',
    content: 'Hello! I\'m JARVIS, your AI trading assistant. I can help you analyze markets, create strategies, execute trades, and manage your trading system. What would you like to do?',
    timestamp: new Date(Date.now() - 60000).toISOString(),
  },
];

function ActionBadge({ action }: { action: ChatAction }) {
  const icons: Record<string, React.ReactNode> = {
    file_created: <FileCode className="h-3 w-3" />,
    trade_executed: <TrendingUp className="h-3 w-3" />,
    strategy_updated: <Settings className="h-3 w-3" />,
    analysis: <BarChart3 className="h-3 w-3" />,
  };

  return (
    <div className="mt-2 flex items-center gap-2 rounded-lg bg-slate-800/50 px-3 py-2 text-xs">
      <div className="text-emerald-400">{icons[action.type]}</div>
      <span className="text-slate-400">{action.description}</span>
    </div>
  );
}

const aiResponses: Record<string, { content: string; actions?: ChatAction[] }> = {
  'analyze': {
    content: 'Based on my analysis of EURUSD on the H1 timeframe:\n\n**Trend:** Bullish (ADX: 32.4)\n**Support:** 1.0842\n**Resistance:** 1.0895\n\nThe pair is showing strong momentum with RSI at 62.3. MACD histogram is positive and expanding. I recommend watching for a pullback to the 1.0855 support zone for a potential long entry.\n\n**Signal:** BUY with 84.7% confidence\n**Suggested SL:** 1.0830\n**Suggested TP:** 1.0910',
    actions: [{ type: 'analysis', description: 'Technical analysis completed for EURUSD H1' }],
  },
  'create': {
    content: 'I\'ve designed a new scalping strategy for GBPUSD:\n\n**Strategy: GBP Scalper v1**\n- Timeframe: M5\n- Entry: EMA 8/21 crossover + RSI confirmation\n- Exit: Fixed TP of 15 pips, SL of 10 pips\n- Risk: 1% per trade\n- Sessions: London & NY overlap only\n\nThe strategy has been saved and is ready for backtesting. Would you like me to run a backtest first?',
    actions: [
      { type: 'file_created', description: 'Created strategy: gbp_scalper_v1.py' },
      { type: 'strategy_updated', description: 'Strategy registered in system' },
    ],
  },
  'performance': {
    content: 'Here\'s your trading performance summary for this month:\n\n**Monthly P&L:** +$5,234.80\n**Win Rate:** 68.3% (237W / 110L)\n**Profit Factor:** 2.14\n**Best Trade:** +$312.45 (XAUUSD)\n**Worst Trade:** -$87.20 (GBPJPY)\n**Average Win:** $87.32\n**Average Loss:** -$42.18\n\nYour performance is above your historical average. The AI Scalper Pro strategy is your top performer this month.',
    actions: [{ type: 'analysis', description: 'Performance report generated' }],
  },
  'risk': {
    content: 'Risk parameters have been updated:\n\n**Max Risk Per Trade:** 1.0% (was 2.0%)\n**Max Daily Drawdown:** 3.0%\n**Max Open Positions:** 5\n**Default Lot Size:** 0.10\n\nAll active strategies have been updated with the new risk settings. The changes will take effect on the next trade signal.',
    actions: [{ type: 'strategy_updated', description: 'Risk parameters updated across all strategies' }],
  },
};

function getAIResponse(message: string): { content: string; actions?: ChatAction[] } {
  const lower = message.toLowerCase();
  if (lower.includes('analyze') || lower.includes('analysis')) return aiResponses['analyze'];
  if (lower.includes('create') || lower.includes('strategy') || lower.includes('scalp')) return aiResponses['create'];
  if (lower.includes('performance') || lower.includes('show') || lower.includes('result')) return aiResponses['performance'];
  if (lower.includes('risk') || lower.includes('adjust') || lower.includes('setting')) return aiResponses['risk'];
  return {
    content: `I understand you want to: "${message}"\n\nI can help with:\n- **Market Analysis** - Analyze any symbol/timeframe\n- **Strategy Creation** - Build and backtest strategies\n- **Trade Management** - Execute and manage trades\n- **Performance Review** - View your trading statistics\n- **Risk Management** - Adjust risk parameters\n\nCould you be more specific about what you'd like me to do?`,
  };
}

export default function ChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>(initialMessages);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async (text?: string) => {
    const message = text || input.trim();
    if (!message) return;

    const userMsg: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: message,
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setIsTyping(true);

    setTimeout(() => {
      const response = getAIResponse(message);
      const aiMsg: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: response.content,
        timestamp: new Date().toISOString(),
        actions: response.actions,
      };
      setMessages((prev) => [...prev, aiMsg]);
      setIsTyping(false);
    }, 1500);
  };

  return (
    <div className="flex h-[calc(100vh-120px)] flex-col">
      <div className="mb-4">
        <h1 className="text-2xl font-bold tracking-tight text-slate-100">AI Chat</h1>
        <p className="mt-1 text-sm text-slate-500">
          Interact with JARVIS to analyze markets, create strategies, and manage trades
        </p>
      </div>

      <div className="flex-1 overflow-y-auto rounded-xl border border-slate-800 bg-slate-900/30 p-4">
        <div className="space-y-4">
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={cn(
                'flex gap-3 fade-in',
                msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'
              )}
            >
              <div
                className={cn(
                  'flex h-8 w-8 shrink-0 items-center justify-center rounded-lg',
                  msg.role === 'user' ? 'bg-blue-500/20' : 'bg-emerald-500/20'
                )}
              >
                {msg.role === 'user' ? (
                  <User className="h-4 w-4 text-blue-400" />
                ) : (
                  <Bot className="h-4 w-4 text-emerald-400" />
                )}
              </div>
              <div
                className={cn(
                  'max-w-[75%] rounded-xl px-4 py-3',
                  msg.role === 'user'
                    ? 'bg-blue-500/10 text-slate-200'
                    : 'bg-slate-800/50 text-slate-300'
                )}
              >
                <div className="whitespace-pre-wrap text-sm leading-relaxed">
                  {msg.content.split(/(\*\*.*?\*\*)/).map((part, i) => {
                    if (part.startsWith('**') && part.endsWith('**')) {
                      return (
                        <strong key={i} className="font-semibold text-slate-100">
                          {part.slice(2, -2)}
                        </strong>
                      );
                    }
                    return <span key={i}>{part}</span>;
                  })}
                </div>
                {msg.actions?.map((action, i) => (
                  <ActionBadge key={i} action={action} />
                ))}
                <p className="mt-2 text-right text-[10px] text-slate-600">
                  {new Date(msg.timestamp).toLocaleTimeString()}
                </p>
              </div>
            </div>
          ))}

          {isTyping && (
            <div className="flex gap-3 fade-in">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-emerald-500/20">
                <Bot className="h-4 w-4 text-emerald-400" />
              </div>
              <div className="rounded-xl bg-slate-800/50 px-4 py-3">
                <div className="flex items-center gap-2 text-sm text-slate-400">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  JARVIS is thinking...
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      <div className="mt-3">
        <div className="mb-3 flex flex-wrap gap-2">
          {exampleCommands.map((cmd) => (
            <button
              key={cmd.label}
              onClick={() => handleSend(cmd.prompt)}
              className="flex items-center gap-1.5 rounded-lg border border-slate-800 bg-slate-900/50 px-3 py-1.5 text-xs font-medium text-slate-400 transition-all hover:border-slate-700 hover:bg-slate-800 hover:text-slate-200"
            >
              <cmd.icon className="h-3 w-3" />
              {cmd.label}
            </button>
          ))}
        </div>

        <div className="flex gap-3">
          <input
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleSend()}
            placeholder="Ask JARVIS anything about your trading..."
            className="flex-1 rounded-xl border border-slate-800 bg-slate-900/50 px-4 py-3 text-sm text-slate-200 placeholder-slate-600 outline-none transition-colors focus:border-emerald-500/50 focus:ring-1 focus:ring-emerald-500/20"
          />
          <button
            onClick={() => handleSend()}
            disabled={!input.trim() || isTyping}
            className="flex items-center gap-2 rounded-xl bg-emerald-600 px-5 py-3 text-sm font-medium text-white transition-colors hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <Send className="h-4 w-4" />
            Send
          </button>
        </div>
      </div>
    </div>
  );
}
