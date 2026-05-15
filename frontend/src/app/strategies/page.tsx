'use client';

import { useState } from 'react';
import {
  Plus,
  Brain,
  BarChart3,
  Zap,
  TrendingUp,
  Play,
  Pause,
  Trash2,
  ChevronRight,
  Target,
  Award,
} from 'lucide-react';
import { cn, formatCurrency, profitColor } from '@/lib/utils';
import type { Strategy } from '@/types';

const mockStrategies: Strategy[] = [
  {
    id: '1', name: 'AI Scalper Pro', type: 'AI', status: 'active',
    description: 'LSTM neural network-based scalping strategy with dynamic risk management. Trained on 5 years of tick data.',
    winRate: 72.4, profitFactor: 2.31, totalTrades: 156, profit: 3420.50,
    symbols: ['EURUSD', 'GBPUSD'], timeframe: 'M5',
    createdAt: '2024-01-15T10:00:00Z', lastUpdated: new Date().toISOString(),
  },
  {
    id: '2', name: 'Trend Follower', type: 'Technical', status: 'active',
    description: 'Multi-timeframe trend following using EMA crossovers, ADX filter, and ATR-based position sizing.',
    winRate: 58.2, profitFactor: 1.87, totalTrades: 89, profit: 1890.30,
    symbols: ['EURUSD', 'USDJPY', 'GBPUSD'], timeframe: 'H1',
    createdAt: '2024-02-01T10:00:00Z', lastUpdated: new Date().toISOString(),
  },
  {
    id: '3', name: 'Mean Reversion', type: 'Hybrid', status: 'paused',
    description: 'Statistical mean reversion with AI-powered entry filter. Uses Bollinger Bands and Z-score.',
    winRate: 65.1, profitFactor: 1.64, totalTrades: 67, profit: 720.80,
    symbols: ['EURUSD'], timeframe: 'M15',
    createdAt: '2024-03-10T10:00:00Z', lastUpdated: new Date().toISOString(),
  },
  {
    id: '4', name: 'Gold Breakout', type: 'Technical', status: 'disabled',
    description: 'Breakout strategy for XAUUSD based on Asian session range with momentum confirmation.',
    winRate: 45.3, profitFactor: 1.12, totalTrades: 34, profit: -120.40,
    symbols: ['XAUUSD'], timeframe: 'H4',
    createdAt: '2024-04-05T10:00:00Z', lastUpdated: new Date().toISOString(),
  },
  {
    id: '5', name: 'News Sentiment', type: 'AI', status: 'active',
    description: 'NLP-based strategy that trades on news sentiment analysis with risk-adjusted position sizing.',
    winRate: 61.8, profitFactor: 1.92, totalTrades: 43, profit: 1250.60,
    symbols: ['EURUSD', 'GBPUSD', 'USDJPY', 'XAUUSD'], timeframe: 'H1',
    createdAt: '2024-05-20T10:00:00Z', lastUpdated: new Date().toISOString(),
  },
];

const typeIcon = { AI: Brain, Technical: BarChart3, Hybrid: Zap, Manual: TrendingUp };
const typeColor = {
  AI: 'bg-purple-500/10 text-purple-400 border-purple-500/20',
  Technical: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
  Hybrid: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
  Manual: 'bg-slate-500/10 text-slate-400 border-slate-500/20',
};

export default function StrategiesPage() {
  const [strategies, setStrategies] = useState(mockStrategies);
  const [view, setView] = useState<'cards' | 'table'>('cards');

  const toggleStrategy = (id: string) => {
    setStrategies((prev) =>
      prev.map((s) =>
        s.id === id
          ? { ...s, status: (s.status === 'active' ? 'paused' : 'active') as Strategy['status'] }
          : s
      )
    );
  };

  const totalProfit = strategies.reduce((sum, s) => sum + s.profit, 0);
  const activeCount = strategies.filter((s) => s.status === 'active').length;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-100">Strategies</h1>
          <p className="mt-1 text-sm text-slate-500">
            Manage and monitor your trading strategies
          </p>
        </div>
        <button className="flex items-center gap-2 rounded-xl bg-emerald-600 px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-emerald-500">
          <Plus className="h-4 w-4" />
          New Strategy
        </button>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <div className="rounded-xl border border-slate-800 bg-slate-900/30 p-4">
          <p className="text-xs font-medium uppercase tracking-wider text-slate-500">Active Strategies</p>
          <p className="mt-2 text-2xl font-bold text-emerald-400">{activeCount}</p>
          <p className="mt-0.5 text-xs text-slate-500">of {strategies.length} total</p>
        </div>
        <div className="rounded-xl border border-slate-800 bg-slate-900/30 p-4">
          <p className="text-xs font-medium uppercase tracking-wider text-slate-500">Total Profit</p>
          <p className={cn('mt-2 text-2xl font-bold', profitColor(totalProfit))}>
            {formatCurrency(totalProfit)}
          </p>
          <p className="mt-0.5 text-xs text-slate-500">All strategies combined</p>
        </div>
        <div className="rounded-xl border border-slate-800 bg-slate-900/30 p-4">
          <p className="text-xs font-medium uppercase tracking-wider text-slate-500">Best Win Rate</p>
          <p className="mt-2 text-2xl font-bold text-blue-400">
            {Math.max(...strategies.map((s) => s.winRate)).toFixed(1)}%
          </p>
          <p className="mt-0.5 text-xs text-slate-500">
            {strategies.reduce((a, b) => (a.winRate > b.winRate ? a : b)).name}
          </p>
        </div>
      </div>

      <div className="space-y-4">
        {strategies.map((strategy) => {
          const Icon = typeIcon[strategy.type] || BarChart3;

          return (
            <div
              key={strategy.id}
              className={cn(
                'rounded-xl border p-5 transition-all hover:border-slate-700',
                strategy.status === 'active'
                  ? 'border-emerald-500/20 bg-emerald-500/5'
                  : strategy.status === 'paused'
                  ? 'border-amber-500/20 bg-amber-500/5'
                  : 'border-slate-800 bg-slate-900/30'
              )}
            >
              <div className="flex items-start justify-between">
                <div className="flex items-start gap-4">
                  <div
                    className={cn(
                      'rounded-xl p-3',
                      strategy.status === 'active'
                        ? 'bg-emerald-500/20'
                        : 'bg-slate-800'
                    )}
                  >
                    <Icon
                      className={cn(
                        'h-6 w-6',
                        strategy.status === 'active' ? 'text-emerald-400' : 'text-slate-500'
                      )}
                    />
                  </div>
                  <div>
                    <div className="flex items-center gap-3">
                      <h3 className="text-lg font-semibold text-slate-200">{strategy.name}</h3>
                      <span className={cn('rounded-full border px-2.5 py-0.5 text-xs font-medium', typeColor[strategy.type])}>
                        {strategy.type}
                      </span>
                      <span
                        className={cn(
                          'rounded-full px-2 py-0.5 text-xs font-medium capitalize',
                          strategy.status === 'active'
                            ? 'bg-emerald-500/10 text-emerald-400'
                            : strategy.status === 'paused'
                            ? 'bg-amber-500/10 text-amber-400'
                            : 'bg-slate-500/10 text-slate-500'
                        )}
                      >
                        {strategy.status}
                      </span>
                    </div>
                    <p className="mt-1 max-w-xl text-sm text-slate-500">{strategy.description}</p>
                    <div className="mt-2 flex items-center gap-2">
                      {strategy.symbols.map((s) => (
                        <span key={s} className="rounded bg-slate-800 px-2 py-0.5 text-xs font-medium text-slate-400">
                          {s}
                        </span>
                      ))}
                      <span className="text-xs text-slate-600">• {strategy.timeframe}</span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() => toggleStrategy(strategy.id)}
                    disabled={strategy.status === 'disabled'}
                    className={cn(
                      'rounded-lg p-2.5 transition-colors',
                      strategy.status === 'active'
                        ? 'bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30'
                        : strategy.status === 'paused'
                        ? 'bg-amber-500/20 text-amber-400 hover:bg-amber-500/30'
                        : 'cursor-not-allowed bg-slate-800 text-slate-600'
                    )}
                  >
                    {strategy.status === 'active' ? (
                      <Pause className="h-5 w-5" />
                    ) : (
                      <Play className="h-5 w-5" />
                    )}
                  </button>
                </div>
              </div>

              <div className="mt-4 grid grid-cols-4 gap-4 border-t border-slate-800/50 pt-4">
                <div className="flex items-center gap-2">
                  <Target className="h-4 w-4 text-slate-500" />
                  <div>
                    <p className="text-xs text-slate-500">Win Rate</p>
                    <p className="text-sm font-semibold text-slate-200">{strategy.winRate}%</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Award className="h-4 w-4 text-slate-500" />
                  <div>
                    <p className="text-xs text-slate-500">Profit Factor</p>
                    <p className="text-sm font-semibold text-slate-200">{strategy.profitFactor}</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <BarChart3 className="h-4 w-4 text-slate-500" />
                  <div>
                    <p className="text-xs text-slate-500">Total Trades</p>
                    <p className="text-sm font-semibold text-slate-200">{strategy.totalTrades}</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <TrendingUp className="h-4 w-4 text-slate-500" />
                  <div>
                    <p className="text-xs text-slate-500">Profit</p>
                    <p className={cn('text-sm font-semibold', profitColor(strategy.profit))}>
                      {formatCurrency(strategy.profit)}
                    </p>
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
