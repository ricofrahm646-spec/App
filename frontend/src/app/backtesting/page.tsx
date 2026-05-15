'use client';

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import EquityChart from '@/components/dashboard/EquityChart';
import { formatCurrency, formatPercent, formatNumber, cn } from '@/lib/utils';
import { Play, Loader2, FlaskConical, BarChart3 } from 'lucide-react';

interface BacktestResult {
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  winrate: number;
  profit_factor: number;
  max_drawdown: number;
  total_profit: number;
  sharpe_ratio: number;
  equity_curve: { time: string; equity: number; balance: number }[];
}

const SYMBOLS = ['XAUUSD', 'EURUSD', 'GBPUSD', 'USDJPY', 'BTCUSD', 'NAS100', 'US30'];
const TIMEFRAMES = ['M1', 'M5', 'M15', 'M30', 'H1', 'H4', 'D1'];

export default function BacktestingPage() {
  const [config, setConfig] = useState({
    symbol: 'XAUUSD',
    timeframe: 'M15',
    strategy: '',
    start_date: '2024-01-01',
    end_date: '2024-12-31',
  });
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<BacktestResult | null>(null);

  const runBacktest = async () => {
    setRunning(true);
    setResult(null);

    // Simulate backtest with mock data
    await new Promise((resolve) => setTimeout(resolve, 2000));

    const trades = 150 + Math.floor(Math.random() * 200);
    const winrate = 0.55 + Math.random() * 0.2;
    const winners = Math.round(trades * winrate);
    const profit = 1000 + Math.random() * 5000;

    const curve: BacktestResult['equity_curve'] = [];
    let eq = 10000;
    let bal = 10000;
    const startDate = new Date(config.start_date);
    const endDate = new Date(config.end_date);
    const days = Math.ceil((endDate.getTime() - startDate.getTime()) / (1000 * 60 * 60 * 24));
    const step = Math.max(1, Math.floor(days / 50));

    for (let i = 0; i <= days; i += step) {
      const d = new Date(startDate);
      d.setDate(d.getDate() + i);
      eq += (Math.random() - 0.42) * 300;
      bal += (Math.random() - 0.42) * 250;
      curve.push({
        time: d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
        equity: Math.round(eq * 100) / 100,
        balance: Math.round(bal * 100) / 100,
      });
    }

    setResult({
      total_trades: trades,
      winning_trades: winners,
      losing_trades: trades - winners,
      winrate,
      profit_factor: 1.2 + Math.random() * 1.5,
      max_drawdown: 0.05 + Math.random() * 0.1,
      total_profit: profit,
      sharpe_ratio: 1 + Math.random() * 2,
      equity_curve: curve,
    });
    setRunning(false);
  };

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h1 className="text-2xl font-bold text-white">Backtesting</h1>
        <p className="text-sm text-slate-400">Test strategies against historical data</p>
      </div>

      {/* Configuration */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base text-white">
            <FlaskConical className="h-4 w-4 text-violet-400" />
            Backtest Configuration
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
            <div>
              <label className="mb-1.5 block text-sm text-slate-400">Symbol</label>
              <select
                value={config.symbol}
                onChange={(e) => setConfig({ ...config, symbol: e.target.value })}
                className="w-full rounded-lg border border-slate-700 bg-slate-800/50 px-3 py-2 text-sm text-white outline-none focus:border-blue-500"
              >
                {SYMBOLS.map((s) => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="mb-1.5 block text-sm text-slate-400">Timeframe</label>
              <select
                value={config.timeframe}
                onChange={(e) => setConfig({ ...config, timeframe: e.target.value })}
                className="w-full rounded-lg border border-slate-700 bg-slate-800/50 px-3 py-2 text-sm text-white outline-none focus:border-blue-500"
              >
                {TIMEFRAMES.map((t) => (
                  <option key={t} value={t}>{t}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="mb-1.5 block text-sm text-slate-400">Strategy</label>
              <input
                type="text"
                value={config.strategy}
                onChange={(e) => setConfig({ ...config, strategy: e.target.value })}
                placeholder="Strategy name"
                className="w-full rounded-lg border border-slate-700 bg-slate-800/50 px-3 py-2 text-sm text-white placeholder-slate-600 outline-none focus:border-blue-500"
              />
            </div>
            <div>
              <label className="mb-1.5 block text-sm text-slate-400">Start Date</label>
              <input
                type="date"
                value={config.start_date}
                onChange={(e) => setConfig({ ...config, start_date: e.target.value })}
                className="w-full rounded-lg border border-slate-700 bg-slate-800/50 px-3 py-2 text-sm text-white outline-none focus:border-blue-500"
              />
            </div>
            <div>
              <label className="mb-1.5 block text-sm text-slate-400">End Date</label>
              <input
                type="date"
                value={config.end_date}
                onChange={(e) => setConfig({ ...config, end_date: e.target.value })}
                className="w-full rounded-lg border border-slate-700 bg-slate-800/50 px-3 py-2 text-sm text-white outline-none focus:border-blue-500"
              />
            </div>
          </div>

          <button
            onClick={runBacktest}
            disabled={running}
            className="mt-4 flex items-center gap-2 rounded-lg bg-violet-600 px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-violet-500 disabled:opacity-50"
          >
            {running ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Running Backtest...
              </>
            ) : (
              <>
                <Play className="h-4 w-4" />
                Run Backtest
              </>
            )}
          </button>
        </CardContent>
      </Card>

      {/* Results */}
      {result && (
        <div className="space-y-6 animate-fade-in">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base text-white">
                <BarChart3 className="h-4 w-4 text-emerald-400" />
                Backtest Results — {config.symbol} {config.timeframe}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
                {[
                  { label: 'Total Trades', value: result.total_trades.toString() },
                  { label: 'Winning', value: result.winning_trades.toString(), color: 'text-emerald-400' },
                  { label: 'Losing', value: result.losing_trades.toString(), color: 'text-red-400' },
                  { label: 'Winrate', value: formatPercent(result.winrate) },
                  { label: 'Profit Factor', value: formatNumber(result.profit_factor) },
                  { label: 'Max Drawdown', value: formatPercent(result.max_drawdown), color: 'text-red-400' },
                  { label: 'Total Profit', value: formatCurrency(result.total_profit), color: result.total_profit >= 0 ? 'text-emerald-400' : 'text-red-400' },
                  { label: 'Sharpe Ratio', value: formatNumber(result.sharpe_ratio) },
                ].map((m) => (
                  <div key={m.label} className="rounded-lg border border-slate-700/30 bg-slate-800/30 p-3">
                    <p className="text-xs text-slate-500">{m.label}</p>
                    <p className={cn('mt-1 text-lg font-semibold', m.color || 'text-white')}>
                      {m.value}
                    </p>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          <EquityChart data={result.equity_curve} />
        </div>
      )}
    </div>
  );
}
