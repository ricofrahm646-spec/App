'use client';

import { useState, useEffect } from 'react';
import { X, ArrowUpRight, ArrowDownRight } from 'lucide-react';
import { cn, formatCurrency, profitColor } from '@/lib/utils';
import type { OpenPosition } from '@/types';

const mockPositions: OpenPosition[] = [
  {
    ticket: 12847570,
    symbol: 'EURUSD',
    type: 'BUY',
    volume: 0.30,
    openPrice: 1.08542,
    currentPrice: 1.08687,
    stopLoss: 1.08300,
    takeProfit: 1.08900,
    profit: 43.50,
    swap: -0.82,
    openTime: new Date(Date.now() - 5400000).toISOString(),
  },
  {
    ticket: 12847571,
    symbol: 'XAUUSD',
    type: 'BUY',
    volume: 0.05,
    openPrice: 2345.80,
    currentPrice: 2352.40,
    stopLoss: 2335.00,
    takeProfit: 2365.00,
    profit: 33.00,
    swap: -0.55,
    openTime: new Date(Date.now() - 10800000).toISOString(),
  },
  {
    ticket: 12847572,
    symbol: 'GBPUSD',
    type: 'SELL',
    volume: 0.20,
    openPrice: 1.27234,
    currentPrice: 1.27301,
    stopLoss: 1.27500,
    takeProfit: 1.26900,
    profit: -13.40,
    swap: 0.32,
    openTime: new Date(Date.now() - 7200000).toISOString(),
  },
];

export function OpenPositions() {
  const [positions, setPositions] = useState<OpenPosition[]>(mockPositions);

  useEffect(() => {
    const interval = setInterval(() => {
      setPositions((prev) =>
        prev.map((pos) => {
          const pip = pos.symbol.includes('JPY') ? 0.01 : 0.00001;
          const xauMultiplier = pos.symbol === 'XAUUSD' ? 100 : 1;
          const change = (Math.random() - 0.5) * pip * 5 * xauMultiplier;
          const newPrice = pos.currentPrice + change;
          const diff = pos.type === 'BUY' ? newPrice - pos.openPrice : pos.openPrice - newPrice;
          const pipValue = pos.symbol.includes('JPY') ? 100 : 100000;
          const newProfit = diff * pos.volume * pipValue / (pos.symbol === 'XAUUSD' ? 1 : 1);

          return {
            ...pos,
            currentPrice: Math.round(newPrice * 100000) / 100000,
            profit: Math.round(newProfit * 100) / 100,
          };
        })
      );
    }, 2000);
    return () => clearInterval(interval);
  }, []);

  const handleClose = (ticket: number) => {
    setPositions((prev) => prev.filter((p) => p.ticket !== ticket));
  };

  const totalProfit = positions.reduce((sum, p) => sum + p.profit, 0);

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/30 p-5">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-400">
          Open Positions
        </h3>
        <div className={cn('text-sm font-bold', profitColor(totalProfit))}>
          {formatCurrency(totalProfit)}
        </div>
      </div>

      {positions.length === 0 ? (
        <p className="py-8 text-center text-sm text-slate-600">No open positions</p>
      ) : (
        <div className="space-y-2">
          {positions.map((pos) => (
            <div
              key={pos.ticket}
              className={cn(
                'flex items-center justify-between rounded-lg border px-4 py-3 transition-all',
                pos.profit >= 0
                  ? 'border-emerald-500/10 bg-emerald-500/5 hover:border-emerald-500/20'
                  : 'border-red-500/10 bg-red-500/5 hover:border-red-500/20'
              )}
            >
              <div className="flex items-center gap-3">
                <div
                  className={cn(
                    'flex h-8 w-8 items-center justify-center rounded-lg',
                    pos.type === 'BUY' ? 'bg-emerald-500/20' : 'bg-red-500/20'
                  )}
                >
                  {pos.type === 'BUY' ? (
                    <ArrowUpRight className="h-4 w-4 text-emerald-400" />
                  ) : (
                    <ArrowDownRight className="h-4 w-4 text-red-400" />
                  )}
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-slate-200">{pos.symbol}</span>
                    <span
                      className={cn(
                        'text-xs font-medium',
                        pos.type === 'BUY' ? 'text-emerald-400' : 'text-red-400'
                      )}
                    >
                      {pos.type}
                    </span>
                    <span className="text-xs text-slate-500">{pos.volume.toFixed(2)} lots</span>
                  </div>
                  <div className="mt-0.5 flex gap-3 text-xs text-slate-500">
                    <span>Entry: {pos.openPrice.toFixed(5)}</span>
                    <span>Current: {pos.currentPrice.toFixed(5)}</span>
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-3">
                <span className={cn('text-sm font-bold', profitColor(pos.profit))}>
                  {formatCurrency(pos.profit)}
                </span>
                <button
                  onClick={() => handleClose(pos.ticket)}
                  className="rounded-lg p-1.5 text-slate-500 transition-colors hover:bg-slate-700 hover:text-red-400"
                  title="Close position"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
