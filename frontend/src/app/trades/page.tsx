'use client';

import { useEffect, useState } from 'react';
import { api, type Trade } from '@/lib/api';
import TradeTable from '@/components/dashboard/TradeTable';
import { Card, CardContent } from '@/components/ui/card';
import { formatCurrency, formatPercent, cn } from '@/lib/utils';
import { BarChart3, TrendingUp, TrendingDown, Target } from 'lucide-react';

type FilterStatus = 'all' | 'open' | 'closed';

export default function TradesPage() {
  const [trades, setTrades] = useState<Trade[]>([]);
  const [filter, setFilter] = useState<FilterStatus>('all');

  const refreshTrades = () => {
    api.getTrades()
      .then((data) => setTrades(data))
      .catch(() => {});
  };

  useEffect(() => {
    let cancelled = false;
    api.getTrades()
      .then((data) => { if (!cancelled) setTrades(data); })
      .catch(() => {});
    return () => { cancelled = true; };
  }, []);

  const filtered = trades.filter((t) => {
    if (filter === 'all') return true;
    return t.status === filter;
  });

  const totalProfit = trades.reduce((sum, t) => sum + t.profit, 0);
  const winningTrades = trades.filter((t) => t.profit > 0).length;
  const losingTrades = trades.filter((t) => t.profit < 0).length;
  const winrate = trades.length > 0 ? winningTrades / trades.length : 0;

  const stats = [
    { label: 'Total Trades', value: trades.length.toString(), icon: BarChart3, color: 'text-blue-400' },
    { label: 'Total Profit', value: formatCurrency(totalProfit), icon: totalProfit >= 0 ? TrendingUp : TrendingDown, color: totalProfit >= 0 ? 'text-emerald-400' : 'text-red-400' },
    { label: 'Winrate', value: formatPercent(winrate), icon: Target, color: 'text-violet-400' },
    { label: 'W/L', value: `${winningTrades} / ${losingTrades}`, icon: BarChart3, color: 'text-amber-400' },
  ];

  const filters: { value: FilterStatus; label: string }[] = [
    { value: 'all', label: 'All' },
    { value: 'open', label: 'Open' },
    { value: 'closed', label: 'Closed' },
  ];

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h1 className="text-2xl font-bold text-white">Trade History</h1>
        <p className="text-sm text-slate-400">Complete trade log and performance</p>
      </div>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {stats.map((s) => {
          const Icon = s.icon;
          return (
            <Card key={s.label}>
              <CardContent className="flex items-center gap-3 p-4">
                <Icon className={cn('h-5 w-5 shrink-0', s.color)} />
                <div>
                  <p className="text-xs text-slate-500">{s.label}</p>
                  <p className="text-lg font-semibold text-white">{s.value}</p>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      <div className="flex gap-2">
        {filters.map((f) => (
          <button
            key={f.value}
            onClick={() => setFilter(f.value)}
            className={cn(
              'rounded-lg px-4 py-2 text-sm font-medium transition-colors',
              filter === f.value
                ? 'bg-blue-600 text-white'
                : 'bg-slate-800 text-slate-400 hover:text-slate-200'
            )}
          >
            {f.label}
          </button>
        ))}
      </div>

      <TradeTable
        trades={filtered}
        title={`${filter === 'all' ? 'All' : filter === 'open' ? 'Open' : 'Closed'} Trades`}
        showClose={filter !== 'closed'}
        onTradeClose={refreshTrades}
      />
    </div>
  );
}
