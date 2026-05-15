'use client';

import { useState, useEffect } from 'react';
import { TrendingUp, TrendingDown, Activity, Globe, Clock } from 'lucide-react';
import { cn, formatNumber, profitColor } from '@/lib/utils';
import type { MarketData, MarketRegime } from '@/types';

const mockMarketData: MarketData[] = [
  { symbol: 'EURUSD', bid: 1.08672, ask: 1.08685, spread: 1.3, change: 0.00045, changePercent: 0.041, high: 1.08745, low: 1.08421, volume: 142500 },
  { symbol: 'GBPUSD', bid: 1.27234, ask: 1.27251, spread: 1.7, change: -0.00123, changePercent: -0.097, high: 1.27412, low: 1.27089, volume: 98300 },
  { symbol: 'USDJPY', bid: 154.321, ask: 154.338, spread: 1.7, change: 0.234, changePercent: 0.152, high: 154.567, low: 153.890, volume: 112800 },
  { symbol: 'XAUUSD', bid: 2352.40, ask: 2352.90, spread: 50, change: 12.30, changePercent: 0.525, high: 2358.70, low: 2338.20, volume: 67200 },
  { symbol: 'GBPJPY', bid: 196.432, ask: 196.465, spread: 3.3, change: -0.187, changePercent: -0.095, high: 196.890, low: 196.112, volume: 45600 },
  { symbol: 'AUDUSD', bid: 0.65432, ask: 0.65448, spread: 1.6, change: 0.00067, changePercent: 0.102, high: 0.65520, low: 0.65312, volume: 56700 },
];

const mockRegime: MarketRegime = {
  regime: 'trending_up',
  confidence: 0.78,
  session: 'london',
};

const regimeLabels: Record<string, string> = {
  trending_up: 'Trending Up',
  trending_down: 'Trending Down',
  ranging: 'Ranging',
  volatile: 'Volatile',
};

const regimeColors: Record<string, string> = {
  trending_up: 'text-emerald-400 bg-emerald-500/10',
  trending_down: 'text-red-400 bg-red-500/10',
  ranging: 'text-blue-400 bg-blue-500/10',
  volatile: 'text-amber-400 bg-amber-500/10',
};

const sessionLabels: Record<string, string> = {
  asian: 'Asian Session',
  london: 'London Session',
  new_york: 'New York Session',
  overlap: 'London/NY Overlap',
};

export function MarketAnalysis() {
  const [marketData, setMarketData] = useState(mockMarketData);
  const regime = mockRegime;

  useEffect(() => {
    const interval = setInterval(() => {
      setMarketData((prev) =>
        prev.map((item) => {
          const pip = item.symbol.includes('JPY')
            ? 0.01
            : item.symbol === 'XAUUSD'
            ? 0.1
            : 0.00001;
          const delta = (Math.random() - 0.5) * pip * 3;
          const newBid = item.bid + delta;
          return {
            ...item,
            bid: newBid,
            ask: newBid + item.spread * pip,
            change: item.change + delta,
            changePercent: ((item.change + delta) / newBid) * 100,
          };
        })
      );
    }, 2500);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/30 p-5">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-400">
          Market Analysis
        </h3>
        <div className="flex items-center gap-3">
          <div className={cn('flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium', regimeColors[regime.regime])}>
            <Activity className="h-3 w-3" />
            {regimeLabels[regime.regime]}
          </div>
          <div className="flex items-center gap-1.5 rounded-full bg-slate-800 px-2.5 py-1 text-xs font-medium text-slate-400">
            <Globe className="h-3 w-3" />
            {sessionLabels[regime.session]}
          </div>
        </div>
      </div>

      <div className="space-y-1">
        {marketData.map((item) => (
          <div
            key={item.symbol}
            className="flex items-center justify-between rounded-lg px-3 py-2 transition-colors hover:bg-slate-800/30"
          >
            <div className="flex items-center gap-3">
              <div className="w-16">
                <span className="text-sm font-semibold text-slate-200">{item.symbol}</span>
              </div>
              <div className="flex items-center gap-1">
                {item.changePercent >= 0 ? (
                  <TrendingUp className="h-3 w-3 text-emerald-400" />
                ) : (
                  <TrendingDown className="h-3 w-3 text-red-400" />
                )}
                <span className={cn('text-xs font-medium', profitColor(item.changePercent))}>
                  {item.changePercent >= 0 ? '+' : ''}{item.changePercent.toFixed(3)}%
                </span>
              </div>
            </div>

            <div className="flex items-center gap-6">
              <div className="text-right">
                <span className="font-mono text-sm text-slate-200">
                  {item.bid.toFixed(item.symbol.includes('JPY') ? 3 : item.symbol === 'XAUUSD' ? 2 : 5)}
                </span>
              </div>
              <div className="w-12 text-right">
                <span className="text-xs text-slate-500">
                  {item.spread.toFixed(1)}
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
