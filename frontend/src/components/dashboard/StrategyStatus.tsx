'use client';

import { useState } from 'react';
import { Play, Pause, Brain, TrendingUp, BarChart3, Zap } from 'lucide-react';
import { cn, statusColor, statusDotColor, formatPercentage } from '@/lib/utils';
import type { Strategy } from '@/types';

const mockStrategies: Strategy[] = [
  {
    id: '1', name: 'AI Scalper Pro', type: 'AI', status: 'active',
    description: 'LSTM-based scalping on major pairs',
    winRate: 72.4, profitFactor: 2.31, totalTrades: 156, profit: 3420.50,
    symbols: ['EURUSD', 'GBPUSD'], timeframe: 'M5',
    createdAt: '2024-01-15', lastUpdated: new Date().toISOString(),
  },
  {
    id: '2', name: 'Trend Follower', type: 'Technical', status: 'active',
    description: 'Multi-timeframe trend following',
    winRate: 58.2, profitFactor: 1.87, totalTrades: 89, profit: 1890.30,
    symbols: ['EURUSD', 'USDJPY', 'GBPUSD'], timeframe: 'H1',
    createdAt: '2024-02-01', lastUpdated: new Date().toISOString(),
  },
  {
    id: '3', name: 'Mean Reversion', type: 'Hybrid', status: 'paused',
    description: 'Statistical mean reversion with AI filter',
    winRate: 65.1, profitFactor: 1.64, totalTrades: 67, profit: 720.80,
    symbols: ['EURUSD'], timeframe: 'M15',
    createdAt: '2024-03-10', lastUpdated: new Date().toISOString(),
  },
  {
    id: '4', name: 'Gold Breakout', type: 'Technical', status: 'disabled',
    description: 'Breakout strategy for XAUUSD',
    winRate: 45.3, profitFactor: 1.12, totalTrades: 34, profit: -120.40,
    symbols: ['XAUUSD'], timeframe: 'H4',
    createdAt: '2024-04-05', lastUpdated: new Date().toISOString(),
  },
];

const typeIcon = {
  AI: Brain,
  Technical: BarChart3,
  Hybrid: Zap,
  Manual: TrendingUp,
};

export function StrategyStatus() {
  const [strategies, setStrategies] = useState(mockStrategies);

  const toggleStrategy = (id: string) => {
    setStrategies((prev) =>
      prev.map((s) =>
        s.id === id
          ? { ...s, status: s.status === 'active' ? 'paused' : 'active' as Strategy['status'] }
          : s
      )
    );
  };

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/30 p-5">
      <h3 className="mb-4 text-sm font-semibold uppercase tracking-wider text-slate-400">
        Active Strategies
      </h3>
      <div className="space-y-3">
        {strategies.map((strategy) => {
          const Icon = typeIcon[strategy.type] || BarChart3;

          return (
            <div
              key={strategy.id}
              className={cn(
                'rounded-lg border p-4 transition-all',
                strategy.status === 'active'
                  ? 'border-emerald-500/20 bg-emerald-500/5'
                  : strategy.status === 'paused'
                  ? 'border-amber-500/20 bg-amber-500/5'
                  : 'border-slate-800 bg-slate-800/20'
              )}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div
                    className={cn(
                      'rounded-lg p-2',
                      strategy.status === 'active'
                        ? 'bg-emerald-500/20'
                        : 'bg-slate-700/50'
                    )}
                  >
                    <Icon
                      className={cn(
                        'h-4 w-4',
                        strategy.status === 'active' ? 'text-emerald-400' : 'text-slate-500'
                      )}
                    />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-slate-200">{strategy.name}</span>
                      <span
                        className={cn(
                          'rounded px-1.5 py-0.5 text-[10px] font-medium uppercase',
                          strategy.type === 'AI'
                            ? 'bg-purple-500/10 text-purple-400'
                            : strategy.type === 'Hybrid'
                            ? 'bg-blue-500/10 text-blue-400'
                            : 'bg-slate-500/10 text-slate-400'
                        )}
                      >
                        {strategy.type}
                      </span>
                    </div>
                    <p className="mt-0.5 text-xs text-slate-500">{strategy.description}</p>
                  </div>
                </div>

                <button
                  onClick={() => toggleStrategy(strategy.id)}
                  disabled={strategy.status === 'disabled'}
                  className={cn(
                    'rounded-lg p-2 transition-colors',
                    strategy.status === 'active'
                      ? 'bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30'
                      : strategy.status === 'paused'
                      ? 'bg-amber-500/20 text-amber-400 hover:bg-amber-500/30'
                      : 'cursor-not-allowed bg-slate-800 text-slate-600'
                  )}
                >
                  {strategy.status === 'active' ? (
                    <Pause className="h-4 w-4" />
                  ) : (
                    <Play className="h-4 w-4" />
                  )}
                </button>
              </div>

              <div className="mt-3 flex gap-4 text-xs">
                <div>
                  <span className="text-slate-500">WR: </span>
                  <span className="font-semibold text-slate-300">{strategy.winRate}%</span>
                </div>
                <div>
                  <span className="text-slate-500">PF: </span>
                  <span className="font-semibold text-slate-300">{strategy.profitFactor}</span>
                </div>
                <div>
                  <span className="text-slate-500">Trades: </span>
                  <span className="font-semibold text-slate-300">{strategy.totalTrades}</span>
                </div>
                <div>
                  <span className="text-slate-500">TF: </span>
                  <span className="font-semibold text-slate-300">{strategy.timeframe}</span>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
