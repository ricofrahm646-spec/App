'use client';

import { useState } from 'react';
import {
  Play,
  Loader2,
  Calendar,
  BarChart3,
  Target,
  TrendingUp,
  Award,
  AlertTriangle,
} from 'lucide-react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { cn, formatCurrency, profitColor } from '@/lib/utils';
import type { EquityPoint } from '@/types';

const strategies = [
  { id: '1', name: 'AI Scalper Pro' },
  { id: '2', name: 'Trend Follower' },
  { id: '3', name: 'Mean Reversion' },
  { id: '4', name: 'Gold Breakout' },
  { id: '5', name: 'News Sentiment' },
];

const symbols = ['EURUSD', 'GBPUSD', 'USDJPY', 'XAUUSD', 'GBPJPY', 'AUDUSD'];
const timeframes = ['M1', 'M5', 'M15', 'M30', 'H1', 'H4', 'D1'];

function generateBacktestEquity(): EquityPoint[] {
  const data: EquityPoint[] = [];
  let balance = 10000;
  let equity = 10000;
  const start = new Date('2024-01-01');

  for (let i = 0; i < 180; i++) {
    const date = new Date(start);
    date.setDate(date.getDate() + i);
    const ret = (Math.random() - 0.44) * 120;
    balance += ret;
    equity = balance + (Math.random() - 0.5) * 50;
    data.push({
      timestamp: date.toISOString(),
      equity: Math.round(equity * 100) / 100,
      balance: Math.round(balance * 100) / 100,
    });
  }
  return data;
}

interface BacktestResults {
  totalTrades: number;
  winRate: number;
  profitFactor: number;
  totalProfit: number;
  maxDrawdown: number;
  sharpeRatio: number;
  averageWin: number;
  averageLoss: number;
  equityCurve: EquityPoint[];
}

const mockResults: BacktestResults = {
  totalTrades: 234,
  winRate: 67.5,
  profitFactor: 2.08,
  totalProfit: 4832.45,
  maxDrawdown: 5.8,
  sharpeRatio: 1.72,
  averageWin: 94.32,
  averageLoss: -45.67,
  equityCurve: generateBacktestEquity(),
};

interface CustomTooltipProps {
  active?: boolean;
  payload?: Array<{ value: number; dataKey: string; color: string }>;
  label?: string;
}

function CustomTooltip({ active, payload, label }: CustomTooltipProps) {
  if (!active || !payload) return null;
  return (
    <div className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 shadow-xl">
      <p className="text-xs text-slate-400">
        {new Date(label || '').toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
      </p>
      {payload.map((entry) => (
        <p key={entry.dataKey} className="text-sm font-semibold" style={{ color: entry.color }}>
          {entry.dataKey === 'equity' ? 'Equity' : 'Balance'}: ${entry.value.toLocaleString('en-US', { minimumFractionDigits: 2 })}
        </p>
      ))}
    </div>
  );
}

export default function BacktestingPage() {
  const [selectedStrategy, setSelectedStrategy] = useState(strategies[0].id);
  const [selectedSymbol, setSelectedSymbol] = useState('EURUSD');
  const [selectedTimeframe, setSelectedTimeframe] = useState('H1');
  const [startDate, setStartDate] = useState('2024-01-01');
  const [endDate, setEndDate] = useState('2024-06-30');
  const [running, setRunning] = useState(false);
  const [results, setResults] = useState<BacktestResults | null>(null);

  const runBacktest = () => {
    setRunning(true);
    setResults(null);
    setTimeout(() => {
      setResults({
        ...mockResults,
        equityCurve: generateBacktestEquity(),
      });
      setRunning(false);
    }, 2500);
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-100">Backtesting</h1>
        <p className="mt-1 text-sm text-slate-500">
          Test strategies against historical data
        </p>
      </div>

      <div className="rounded-xl border border-slate-800 bg-slate-900/30 p-5">
        <h3 className="mb-4 text-sm font-semibold uppercase tracking-wider text-slate-400">
          Configuration
        </h3>
        <div className="grid gap-4 md:grid-cols-3 lg:grid-cols-6">
          <div>
            <label className="mb-1.5 block text-xs font-medium text-slate-500">Strategy</label>
            <select
              value={selectedStrategy}
              onChange={(e) => setSelectedStrategy(e.target.value)}
              className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-200 outline-none focus:border-emerald-500/50"
            >
              {strategies.map((s) => (
                <option key={s.id} value={s.id}>{s.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1.5 block text-xs font-medium text-slate-500">Symbol</label>
            <select
              value={selectedSymbol}
              onChange={(e) => setSelectedSymbol(e.target.value)}
              className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-200 outline-none focus:border-emerald-500/50"
            >
              {symbols.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1.5 block text-xs font-medium text-slate-500">Timeframe</label>
            <select
              value={selectedTimeframe}
              onChange={(e) => setSelectedTimeframe(e.target.value)}
              className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-200 outline-none focus:border-emerald-500/50"
            >
              {timeframes.map((t) => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1.5 block text-xs font-medium text-slate-500">Start Date</label>
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-200 outline-none focus:border-emerald-500/50"
            />
          </div>
          <div>
            <label className="mb-1.5 block text-xs font-medium text-slate-500">End Date</label>
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-200 outline-none focus:border-emerald-500/50"
            />
          </div>
          <div className="flex items-end">
            <button
              onClick={runBacktest}
              disabled={running}
              className="flex w-full items-center justify-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-emerald-500 disabled:opacity-50"
            >
              {running ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Running...
                </>
              ) : (
                <>
                  <Play className="h-4 w-4" />
                  Run Backtest
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {running && (
        <div className="flex items-center justify-center rounded-xl border border-slate-800 bg-slate-900/30 py-20">
          <div className="text-center">
            <Loader2 className="mx-auto h-10 w-10 animate-spin text-emerald-400" />
            <p className="mt-4 text-sm font-medium text-slate-400">Running backtest...</p>
            <p className="mt-1 text-xs text-slate-600">
              Testing {strategies.find((s) => s.id === selectedStrategy)?.name} on {selectedSymbol} {selectedTimeframe}
            </p>
          </div>
        </div>
      )}

      {results && !running && (
        <>
          <div className="grid grid-cols-2 gap-4 md:grid-cols-4 lg:grid-cols-8">
            {[
              { label: 'Total Trades', value: results.totalTrades.toString(), icon: BarChart3, color: 'text-blue-400' },
              { label: 'Win Rate', value: `${results.winRate}%`, icon: Target, color: 'text-emerald-400' },
              { label: 'Profit Factor', value: results.profitFactor.toFixed(2), icon: Award, color: 'text-purple-400' },
              { label: 'Total Profit', value: formatCurrency(results.totalProfit), icon: TrendingUp, color: profitColor(results.totalProfit) },
              { label: 'Max Drawdown', value: `${results.maxDrawdown}%`, icon: AlertTriangle, color: 'text-red-400' },
              { label: 'Sharpe Ratio', value: results.sharpeRatio.toFixed(2), icon: Award, color: 'text-amber-400' },
              { label: 'Avg Win', value: formatCurrency(results.averageWin), icon: TrendingUp, color: 'text-emerald-400' },
              { label: 'Avg Loss', value: formatCurrency(results.averageLoss), icon: AlertTriangle, color: 'text-red-400' },
            ].map((metric) => (
              <div key={metric.label} className="rounded-xl border border-slate-800 bg-slate-900/30 p-3">
                <div className="flex items-center gap-1.5">
                  <metric.icon className={cn('h-3 w-3', metric.color)} />
                  <span className="text-[10px] font-medium uppercase tracking-wider text-slate-500">{metric.label}</span>
                </div>
                <p className={cn('mt-1.5 text-lg font-bold', metric.color)}>{metric.value}</p>
              </div>
            ))}
          </div>

          <div className="rounded-xl border border-slate-800 bg-slate-900/30 p-5">
            <h3 className="mb-4 text-sm font-semibold uppercase tracking-wider text-slate-400">
              Equity Curve
            </h3>
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={results.equityCurve}>
                  <defs>
                    <linearGradient id="btEquityGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#34d399" stopOpacity={0.2} />
                      <stop offset="100%" stopColor="#34d399" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                  <XAxis
                    dataKey="timestamp"
                    tickFormatter={(v) => new Date(v).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                    stroke="#475569"
                    tick={{ fill: '#64748b', fontSize: 11 }}
                  />
                  <YAxis
                    stroke="#475569"
                    tick={{ fill: '#64748b', fontSize: 11 }}
                    tickFormatter={(v) => `$${(v / 1000).toFixed(1)}k`}
                  />
                  <Tooltip content={<CustomTooltip />} />
                  <Area type="monotone" dataKey="balance" stroke="#60a5fa" strokeWidth={1.5} fill="none" dot={false} />
                  <Area type="monotone" dataKey="equity" stroke="#34d399" strokeWidth={2} fill="url(#btEquityGrad)" dot={false} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>
        </>
      )}

      {!results && !running && (
        <div className="flex items-center justify-center rounded-xl border border-dashed border-slate-800 py-20">
          <div className="text-center">
            <BarChart3 className="mx-auto h-12 w-12 text-slate-700" />
            <p className="mt-4 text-sm font-medium text-slate-500">No backtest results yet</p>
            <p className="mt-1 text-xs text-slate-600">
              Configure parameters above and run a backtest
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
