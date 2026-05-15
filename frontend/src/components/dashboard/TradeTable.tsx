'use client';

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { formatCurrency, cn } from '@/lib/utils';
import type { Trade } from '@/lib/api';
import { api } from '@/lib/api';
import { X, ArrowUpDown, Inbox } from 'lucide-react';
import { format } from 'date-fns';

interface TradeTableProps {
  trades: Trade[];
  title?: string;
  showClose?: boolean;
  onTradeClose?: () => void;
}

type SortKey = keyof Trade;
type SortDir = 'asc' | 'desc';

export default function TradeTable({
  trades,
  title = 'Trades',
  showClose = false,
  onTradeClose,
}: TradeTableProps) {
  const [sortKey, setSortKey] = useState<SortKey>('open_time');
  const [sortDir, setSortDir] = useState<SortDir>('desc');
  const [closingId, setClosingId] = useState<number | null>(null);

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir(sortDir === 'asc' ? 'desc' : 'asc');
    } else {
      setSortKey(key);
      setSortDir('desc');
    }
  };

  const sorted = [...trades].sort((a, b) => {
    const aVal = a[sortKey];
    const bVal = b[sortKey];
    if (aVal == null && bVal == null) return 0;
    if (aVal == null) return 1;
    if (bVal == null) return -1;
    const cmp = aVal < bVal ? -1 : aVal > bVal ? 1 : 0;
    return sortDir === 'asc' ? cmp : -cmp;
  });

  const handleClose = async (id: number) => {
    setClosingId(id);
    try {
      await api.closeTrade(id);
      onTradeClose?.();
    } catch {
      /* silently fail */
    } finally {
      setClosingId(null);
    }
  };

  const columns: { key: SortKey; label: string }[] = [
    { key: 'symbol', label: 'Symbol' },
    { key: 'direction', label: 'Direction' },
    { key: 'volume', label: 'Volume' },
    { key: 'open_price', label: 'Entry' },
    { key: 'sl', label: 'SL' },
    { key: 'tp', label: 'TP' },
    { key: 'profit', label: 'Profit' },
    { key: 'status', label: 'Status' },
    { key: 'strategy_name', label: 'Strategy' },
    { key: 'open_time', label: 'Time' },
  ];

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base text-white">{title}</CardTitle>
      </CardHeader>
      <CardContent className="overflow-x-auto">
        {trades.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-slate-500">
            <Inbox className="mb-3 h-10 w-10" />
            <p className="text-sm">No trades to display</p>
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-700/50">
                {columns.map((col) => (
                  <th
                    key={col.key}
                    className="cursor-pointer whitespace-nowrap px-3 py-2 text-left text-xs font-medium uppercase tracking-wider text-slate-400 hover:text-slate-200"
                    onClick={() => handleSort(col.key)}
                  >
                    <span className="inline-flex items-center gap-1">
                      {col.label}
                      {sortKey === col.key && (
                        <ArrowUpDown className="h-3 w-3" />
                      )}
                    </span>
                  </th>
                ))}
                {showClose && (
                  <th className="px-3 py-2 text-xs font-medium uppercase tracking-wider text-slate-400">
                    Action
                  </th>
                )}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700/30">
              {sorted.map((trade) => (
                <tr
                  key={trade.id}
                  className="transition-colors hover:bg-slate-700/20"
                >
                  <td className="whitespace-nowrap px-3 py-2.5 font-medium text-white">
                    {trade.symbol}
                  </td>
                  <td className="whitespace-nowrap px-3 py-2.5">
                    <span
                      className={cn(
                        'rounded-md px-2 py-0.5 text-xs font-semibold',
                        trade.direction === 'BUY'
                          ? 'bg-emerald-500/20 text-emerald-400'
                          : 'bg-red-500/20 text-red-400'
                      )}
                    >
                      {trade.direction}
                    </span>
                  </td>
                  <td className="whitespace-nowrap px-3 py-2.5 text-slate-300">
                    {trade.volume}
                  </td>
                  <td className="whitespace-nowrap px-3 py-2.5 text-slate-300">
                    {trade.open_price.toFixed(5)}
                  </td>
                  <td className="whitespace-nowrap px-3 py-2.5 text-slate-400">
                    {trade.sl?.toFixed(5) ?? '—'}
                  </td>
                  <td className="whitespace-nowrap px-3 py-2.5 text-slate-400">
                    {trade.tp?.toFixed(5) ?? '—'}
                  </td>
                  <td
                    className={cn(
                      'whitespace-nowrap px-3 py-2.5 font-medium',
                      trade.profit >= 0 ? 'text-emerald-400' : 'text-red-400'
                    )}
                  >
                    {formatCurrency(trade.profit)}
                  </td>
                  <td className="whitespace-nowrap px-3 py-2.5">
                    <span
                      className={cn(
                        'rounded-full px-2 py-0.5 text-xs',
                        trade.status === 'open'
                          ? 'bg-blue-500/20 text-blue-400'
                          : 'bg-slate-600/30 text-slate-400'
                      )}
                    >
                      {trade.status}
                    </span>
                  </td>
                  <td className="whitespace-nowrap px-3 py-2.5 text-slate-400">
                    {trade.strategy_name}
                  </td>
                  <td className="whitespace-nowrap px-3 py-2.5 text-slate-500">
                    {format(new Date(trade.open_time), 'MMM dd HH:mm')}
                  </td>
                  {showClose && (
                    <td className="whitespace-nowrap px-3 py-2.5">
                      <button
                        onClick={() => handleClose(trade.id)}
                        disabled={closingId === trade.id}
                        className="rounded-md p-1 text-red-400 transition-colors hover:bg-red-500/20 disabled:opacity-50"
                      >
                        <X className="h-4 w-4" />
                      </button>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </CardContent>
    </Card>
  );
}
