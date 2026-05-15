'use client';

import { useState, useEffect } from 'react';
import {
  ArrowUpRight,
  ArrowDownRight,
  X,
  Clock,
  TrendingUp,
  TrendingDown,
  AlertCircle,
} from 'lucide-react';
import { cn, formatCurrency, profitColor, formatDate } from '@/lib/utils';
import type { OpenPosition, Trade } from '@/types';

const symbols = ['EURUSD', 'GBPUSD', 'USDJPY', 'XAUUSD', 'GBPJPY', 'AUDUSD', 'NZDUSD', 'USDCHF'];

const mockPrices: Record<string, { bid: number; ask: number }> = {
  EURUSD: { bid: 1.08672, ask: 1.08685 },
  GBPUSD: { bid: 1.27234, ask: 1.27251 },
  USDJPY: { bid: 154.321, ask: 154.338 },
  XAUUSD: { bid: 2352.40, ask: 2352.90 },
  GBPJPY: { bid: 196.432, ask: 196.465 },
  AUDUSD: { bid: 0.65432, ask: 0.65448 },
  NZDUSD: { bid: 0.60123, ask: 0.60141 },
  USDCHF: { bid: 0.89234, ask: 0.89252 },
};

const mockOpenPositions: OpenPosition[] = [
  {
    ticket: 12847570, symbol: 'EURUSD', type: 'BUY', volume: 0.30,
    openPrice: 1.08542, currentPrice: 1.08687, stopLoss: 1.08300, takeProfit: 1.08900,
    profit: 43.50, swap: -0.82, openTime: new Date(Date.now() - 5400000).toISOString(),
  },
  {
    ticket: 12847571, symbol: 'XAUUSD', type: 'BUY', volume: 0.05,
    openPrice: 2345.80, currentPrice: 2352.40, stopLoss: 2335.00, takeProfit: 2365.00,
    profit: 33.00, swap: -0.55, openTime: new Date(Date.now() - 10800000).toISOString(),
  },
];

const mockTradeLog: Trade[] = [
  {
    id: '1', ticket: 12847561, symbol: 'EURUSD', type: 'BUY', volume: 0.50,
    openPrice: 1.08432, closePrice: 1.08671, stopLoss: 1.08200, takeProfit: 1.08700,
    profit: 119.50, commission: -3.50, swap: -0.82,
    openTime: new Date(Date.now() - 7200000).toISOString(),
    closeTime: new Date(Date.now() - 3600000).toISOString(), comment: 'Manual',
  },
  {
    id: '2', ticket: 12847562, symbol: 'GBPUSD', type: 'SELL', volume: 0.30,
    openPrice: 1.27145, closePrice: 1.26932, stopLoss: 1.27400, takeProfit: 1.26900,
    profit: 63.90, commission: -2.10, swap: 0.45,
    openTime: new Date(Date.now() - 14400000).toISOString(),
    closeTime: new Date(Date.now() - 10800000).toISOString(), comment: 'Manual',
  },
  {
    id: '3', ticket: 12847563, symbol: 'USDJPY', type: 'BUY', volume: 0.20,
    openPrice: 154.321, closePrice: 154.112, stopLoss: 154.100, takeProfit: 154.600,
    profit: -27.80, commission: -1.40, swap: 0.12,
    openTime: new Date(Date.now() - 21600000).toISOString(),
    closeTime: new Date(Date.now() - 18000000).toISOString(), comment: 'Manual',
  },
];

export default function TradingPage() {
  const [selectedSymbol, setSelectedSymbol] = useState('EURUSD');
  const [volume, setVolume] = useState('0.10');
  const [stopLoss, setStopLoss] = useState('');
  const [takeProfit, setTakeProfit] = useState('');
  const [positions, setPositions] = useState(mockOpenPositions);
  const [tradeLog, setTradeLog] = useState(mockTradeLog);
  const [prices, setPrices] = useState(mockPrices);

  useEffect(() => {
    const interval = setInterval(() => {
      setPrices((prev) => {
        const updated = { ...prev };
        for (const sym of Object.keys(updated)) {
          const pip = sym.includes('JPY') ? 0.01 : sym === 'XAUUSD' ? 0.1 : 0.00001;
          const delta = (Math.random() - 0.5) * pip * 3;
          updated[sym] = {
            bid: updated[sym].bid + delta,
            ask: updated[sym].ask + delta,
          };
        }
        return updated;
      });
    }, 2000);
    return () => clearInterval(interval);
  }, []);

  const currentPrice = prices[selectedSymbol];
  const decimals = selectedSymbol.includes('JPY') ? 3 : selectedSymbol === 'XAUUSD' ? 2 : 5;

  const handleTrade = (type: 'BUY' | 'SELL') => {
    const price = type === 'BUY' ? currentPrice.ask : currentPrice.bid;
    const newPosition: OpenPosition = {
      ticket: Date.now(),
      symbol: selectedSymbol,
      type,
      volume: parseFloat(volume),
      openPrice: price,
      currentPrice: price,
      stopLoss: stopLoss ? parseFloat(stopLoss) : null,
      takeProfit: takeProfit ? parseFloat(takeProfit) : null,
      profit: 0,
      swap: 0,
      openTime: new Date().toISOString(),
    };
    setPositions((prev) => [newPosition, ...prev]);
  };

  const handleClose = (ticket: number) => {
    const pos = positions.find((p) => p.ticket === ticket);
    if (pos) {
      const closedTrade: Trade = {
        id: ticket.toString(),
        ticket,
        symbol: pos.symbol,
        type: pos.type,
        volume: pos.volume,
        openPrice: pos.openPrice,
        closePrice: pos.currentPrice,
        stopLoss: pos.stopLoss,
        takeProfit: pos.takeProfit,
        profit: pos.profit,
        commission: -1.50,
        swap: pos.swap,
        openTime: pos.openTime,
        closeTime: new Date().toISOString(),
        comment: 'Manual Close',
      };
      setTradeLog((prev) => [closedTrade, ...prev]);
    }
    setPositions((prev) => prev.filter((p) => p.ticket !== ticket));
  };

  const totalProfit = positions.reduce((sum, p) => sum + p.profit, 0);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-100">Trading</h1>
        <p className="mt-1 text-sm text-slate-500">Manual trade execution and management</p>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="rounded-xl border border-slate-800 bg-slate-900/30 p-5">
          <h3 className="mb-4 text-sm font-semibold uppercase tracking-wider text-slate-400">
            Quick Trade
          </h3>

          <div className="space-y-4">
            <div>
              <label className="mb-1.5 block text-xs font-medium text-slate-500">Symbol</label>
              <select
                value={selectedSymbol}
                onChange={(e) => setSelectedSymbol(e.target.value)}
                className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2.5 text-sm font-medium text-slate-200 outline-none focus:border-emerald-500/50"
              >
                {symbols.map((s) => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
            </div>

            <div className="rounded-lg bg-slate-800/50 p-3 text-center">
              <div className="flex items-center justify-center gap-6">
                <div>
                  <p className="text-xs text-slate-500">Bid</p>
                  <p className="font-mono text-lg font-bold text-red-400">
                    {currentPrice.bid.toFixed(decimals)}
                  </p>
                </div>
                <div className="h-8 w-px bg-slate-700" />
                <div>
                  <p className="text-xs text-slate-500">Ask</p>
                  <p className="font-mono text-lg font-bold text-emerald-400">
                    {currentPrice.ask.toFixed(decimals)}
                  </p>
                </div>
              </div>
              <p className="mt-1 text-xs text-slate-600">
                Spread: {((currentPrice.ask - currentPrice.bid) * (selectedSymbol.includes('JPY') ? 100 : 100000)).toFixed(1)} pts
              </p>
            </div>

            <div>
              <label className="mb-1.5 block text-xs font-medium text-slate-500">Volume (lots)</label>
              <input
                type="number"
                value={volume}
                onChange={(e) => setVolume(e.target.value)}
                step="0.01"
                min="0.01"
                className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2.5 text-sm text-slate-200 outline-none focus:border-emerald-500/50"
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="mb-1.5 block text-xs font-medium text-slate-500">Stop Loss</label>
                <input
                  type="number"
                  value={stopLoss}
                  onChange={(e) => setStopLoss(e.target.value)}
                  placeholder="Optional"
                  step="0.00001"
                  className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2.5 text-sm text-slate-200 placeholder-slate-600 outline-none focus:border-emerald-500/50"
                />
              </div>
              <div>
                <label className="mb-1.5 block text-xs font-medium text-slate-500">Take Profit</label>
                <input
                  type="number"
                  value={takeProfit}
                  onChange={(e) => setTakeProfit(e.target.value)}
                  placeholder="Optional"
                  step="0.00001"
                  className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2.5 text-sm text-slate-200 placeholder-slate-600 outline-none focus:border-emerald-500/50"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <button
                onClick={() => handleTrade('BUY')}
                className="flex items-center justify-center gap-2 rounded-xl bg-emerald-600 py-3.5 text-sm font-bold text-white transition-colors hover:bg-emerald-500"
              >
                <ArrowUpRight className="h-5 w-5" />
                BUY
              </button>
              <button
                onClick={() => handleTrade('SELL')}
                className="flex items-center justify-center gap-2 rounded-xl bg-red-600 py-3.5 text-sm font-bold text-white transition-colors hover:bg-red-500"
              >
                <ArrowDownRight className="h-5 w-5" />
                SELL
              </button>
            </div>
          </div>
        </div>

        <div className="lg:col-span-2 space-y-6">
          <div className="rounded-xl border border-slate-800 bg-slate-900/30 p-5">
            <div className="mb-4 flex items-center justify-between">
              <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-400">
                Open Positions ({positions.length})
              </h3>
              <span className={cn('text-sm font-bold', profitColor(totalProfit))}>
                {formatCurrency(totalProfit)}
              </span>
            </div>

            {positions.length === 0 ? (
              <p className="py-8 text-center text-sm text-slate-600">No open positions</p>
            ) : (
              <div className="space-y-2">
                {positions.map((pos) => (
                  <div
                    key={pos.ticket}
                    className={cn(
                      'flex items-center justify-between rounded-lg border px-4 py-3',
                      pos.profit >= 0
                        ? 'border-emerald-500/10 bg-emerald-500/5'
                        : 'border-red-500/10 bg-red-500/5'
                    )}
                  >
                    <div className="flex items-center gap-3">
                      {pos.type === 'BUY' ? (
                        <ArrowUpRight className="h-5 w-5 text-emerald-400" />
                      ) : (
                        <ArrowDownRight className="h-5 w-5 text-red-400" />
                      )}
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-semibold text-slate-200">{pos.symbol}</span>
                          <span className={cn('text-xs font-medium', pos.type === 'BUY' ? 'text-emerald-400' : 'text-red-400')}>
                            {pos.type}
                          </span>
                          <span className="text-xs text-slate-500">{pos.volume} lots</span>
                        </div>
                        <div className="mt-0.5 text-xs text-slate-500">
                          Entry: {pos.openPrice.toFixed(5)} | #{pos.ticket}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className={cn('font-bold', profitColor(pos.profit))}>
                        {formatCurrency(pos.profit)}
                      </span>
                      <button
                        onClick={() => handleClose(pos.ticket)}
                        className="rounded-lg p-1.5 text-slate-500 hover:bg-slate-700 hover:text-red-400"
                      >
                        <X className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="rounded-xl border border-slate-800 bg-slate-900/30 p-5">
            <h3 className="mb-4 text-sm font-semibold uppercase tracking-wider text-slate-400">
              Trade Log
            </h3>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-800">
                    <th className="px-3 py-2 text-left text-xs font-medium uppercase text-slate-500">Symbol</th>
                    <th className="px-3 py-2 text-left text-xs font-medium uppercase text-slate-500">Type</th>
                    <th className="px-3 py-2 text-left text-xs font-medium uppercase text-slate-500">Volume</th>
                    <th className="px-3 py-2 text-left text-xs font-medium uppercase text-slate-500">Open</th>
                    <th className="px-3 py-2 text-left text-xs font-medium uppercase text-slate-500">Close</th>
                    <th className="px-3 py-2 text-left text-xs font-medium uppercase text-slate-500">Profit</th>
                    <th className="px-3 py-2 text-left text-xs font-medium uppercase text-slate-500">Time</th>
                  </tr>
                </thead>
                <tbody>
                  {tradeLog.map((trade) => (
                    <tr key={trade.id} className="border-b border-slate-800/50 hover:bg-slate-800/20">
                      <td className="px-3 py-2 font-medium text-slate-200">{trade.symbol}</td>
                      <td className="px-3 py-2">
                        <span className={cn('rounded px-1.5 py-0.5 text-xs font-semibold', trade.type === 'BUY' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-red-500/10 text-red-400')}>
                          {trade.type}
                        </span>
                      </td>
                      <td className="px-3 py-2 text-slate-300">{trade.volume}</td>
                      <td className="px-3 py-2 font-mono text-xs text-slate-400">{trade.openPrice.toFixed(5)}</td>
                      <td className="px-3 py-2 font-mono text-xs text-slate-400">{trade.closePrice?.toFixed(5)}</td>
                      <td className={cn('px-3 py-2 font-semibold', profitColor(trade.profit))}>{formatCurrency(trade.profit)}</td>
                      <td className="px-3 py-2 text-xs text-slate-500">{trade.closeTime ? formatDate(trade.closeTime) : ''}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
