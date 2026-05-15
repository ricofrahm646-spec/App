'use client';

import { useState } from 'react';
import { ArrowUpDown, ArrowUp, ArrowDown } from 'lucide-react';
import { cn, formatCurrency, formatDate, profitColor } from '@/lib/utils';
import type { Trade } from '@/types';

const mockTrades: Trade[] = [
  {
    id: '1', ticket: 12847561, symbol: 'EURUSD', type: 'BUY', volume: 0.50,
    openPrice: 1.08432, closePrice: 1.08671, stopLoss: 1.08200, takeProfit: 1.08700,
    profit: 119.50, commission: -3.50, swap: -0.82,
    openTime: new Date(Date.now() - 7200000).toISOString(),
    closeTime: new Date(Date.now() - 3600000).toISOString(), comment: 'AI Scalper',
  },
  {
    id: '2', ticket: 12847562, symbol: 'GBPUSD', type: 'SELL', volume: 0.30,
    openPrice: 1.27145, closePrice: 1.26932, stopLoss: 1.27400, takeProfit: 1.26900,
    profit: 63.90, commission: -2.10, swap: 0.45,
    openTime: new Date(Date.now() - 14400000).toISOString(),
    closeTime: new Date(Date.now() - 10800000).toISOString(), comment: 'Trend Follow',
  },
  {
    id: '3', ticket: 12847563, symbol: 'USDJPY', type: 'BUY', volume: 0.20,
    openPrice: 154.321, closePrice: 154.112, stopLoss: 154.100, takeProfit: 154.600,
    profit: -27.80, commission: -1.40, swap: 0.12,
    openTime: new Date(Date.now() - 21600000).toISOString(),
    closeTime: new Date(Date.now() - 18000000).toISOString(), comment: 'Manual',
  },
  {
    id: '4', ticket: 12847564, symbol: 'XAUUSD', type: 'BUY', volume: 0.10,
    openPrice: 2341.50, closePrice: 2358.30, stopLoss: 2330.00, takeProfit: 2360.00,
    profit: 168.00, commission: -5.00, swap: -1.20,
    openTime: new Date(Date.now() - 28800000).toISOString(),
    closeTime: new Date(Date.now() - 25200000).toISOString(), comment: 'AI Breakout',
  },
  {
    id: '5', ticket: 12847565, symbol: 'EURUSD', type: 'SELL', volume: 0.25,
    openPrice: 1.08712, closePrice: 1.08845, stopLoss: 1.08900, takeProfit: 1.08500,
    profit: -33.25, commission: -1.75, swap: 0.30,
    openTime: new Date(Date.now() - 36000000).toISOString(),
    closeTime: new Date(Date.now() - 32400000).toISOString(), comment: 'Mean Reversion',
  },
  {
    id: '6', ticket: 12847566, symbol: 'GBPJPY', type: 'BUY', volume: 0.15,
    openPrice: 196.432, closePrice: 196.891, stopLoss: 196.100, takeProfit: 197.000,
    profit: 45.65, commission: -2.25, swap: -0.55,
    openTime: new Date(Date.now() - 43200000).toISOString(),
    closeTime: new Date(Date.now() - 39600000).toISOString(), comment: 'AI Scalper',
  },
];

type SortKey = 'closeTime' | 'profit' | 'symbol' | 'volume';

export function TradeHistory() {
  const [sortKey, setSortKey] = useState<SortKey>('closeTime');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir(sortDir === 'asc' ? 'desc' : 'asc');
    } else {
      setSortKey(key);
      setSortDir('desc');
    }
  };

  const sorted = [...mockTrades].sort((a, b) => {
    let aVal: number | string, bVal: number | string;
    switch (sortKey) {
      case 'profit': aVal = a.profit; bVal = b.profit; break;
      case 'symbol': aVal = a.symbol; bVal = b.symbol; break;
      case 'volume': aVal = a.volume; bVal = b.volume; break;
      default: aVal = a.closeTime || ''; bVal = b.closeTime || '';
    }
    if (aVal < bVal) return sortDir === 'asc' ? -1 : 1;
    if (aVal > bVal) return sortDir === 'asc' ? 1 : -1;
    return 0;
  });

  const SortIcon = ({ column }: { column: SortKey }) => {
    if (sortKey !== column) return <ArrowUpDown className="h-3 w-3 text-slate-600" />;
    return sortDir === 'asc'
      ? <ArrowUp className="h-3 w-3 text-emerald-400" />
      : <ArrowDown className="h-3 w-3 text-emerald-400" />;
  };

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/30 p-5">
      <h3 className="mb-4 text-sm font-semibold uppercase tracking-wider text-slate-400">
        Trade History
      </h3>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-800">
              {[
                { key: 'symbol' as SortKey, label: 'Symbol' },
                { key: null, label: 'Type' },
                { key: 'volume' as SortKey, label: 'Volume' },
                { key: null, label: 'Open' },
                { key: null, label: 'Close' },
                { key: 'profit' as SortKey, label: 'Profit' },
                { key: 'closeTime' as SortKey, label: 'Time' },
              ].map((col, i) => (
                <th
                  key={i}
                  className={cn(
                    'px-3 py-2 text-left text-xs font-medium uppercase tracking-wider text-slate-500',
                    col.key && 'cursor-pointer hover:text-slate-300'
                  )}
                  onClick={() => col.key && handleSort(col.key)}
                >
                  <div className="flex items-center gap-1">
                    {col.label}
                    {col.key && <SortIcon column={col.key} />}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sorted.map((trade) => (
              <tr
                key={trade.id}
                className="border-b border-slate-800/50 transition-colors hover:bg-slate-800/20"
              >
                <td className="px-3 py-2.5 font-medium text-slate-200">
                  {trade.symbol}
                </td>
                <td className="px-3 py-2.5">
                  <span
                    className={cn(
                      'rounded px-1.5 py-0.5 text-xs font-semibold',
                      trade.type === 'BUY'
                        ? 'bg-emerald-500/10 text-emerald-400'
                        : 'bg-red-500/10 text-red-400'
                    )}
                  >
                    {trade.type}
                  </span>
                </td>
                <td className="px-3 py-2.5 text-slate-300">{trade.volume.toFixed(2)}</td>
                <td className="px-3 py-2.5 font-mono text-xs text-slate-400">
                  {trade.openPrice.toFixed(trade.symbol.includes('JPY') ? 3 : 5)}
                </td>
                <td className="px-3 py-2.5 font-mono text-xs text-slate-400">
                  {trade.closePrice?.toFixed(trade.symbol.includes('JPY') ? 3 : 5) ?? '—'}
                </td>
                <td className={cn('px-3 py-2.5 font-semibold', profitColor(trade.profit))}>
                  {formatCurrency(trade.profit)}
                </td>
                <td className="px-3 py-2.5 text-xs text-slate-500">
                  {trade.closeTime ? formatDate(trade.closeTime) : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
