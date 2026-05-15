'use client'

import { useState } from 'react'
import { useJarvisStore } from '@/store/useJarvisStore'
import { BacktestResult } from '@/types'
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
} from 'recharts'
import {
  BarChart2,
  Play,
  Loader2,
  TrendingUp,
  TrendingDown,
  Target,
  Award,
  AlertTriangle,
  CheckCircle,
  XCircle,
} from 'lucide-react'
import toast from 'react-hot-toast'
import clsx from 'clsx'

const TIMEFRAMES = ['M1', 'M5', 'M15', 'M30', 'H1', 'H4', 'D1']
const SYMBOLS = ['XAUUSD', 'EURUSD', 'GBPUSD', 'USDJPY', 'BTCUSD', 'USDCHF', 'AUDUSD']

function generateMockBacktest(): BacktestResult {
  const totalTrades = Math.floor(Math.random() * 300) + 100
  const winTrades = Math.floor(totalTrades * (0.5 + Math.random() * 0.3))
  const lossTrades = totalTrades - winTrades

  let equity = 10000
  const equityCurve = [equity]
  for (let i = 0; i < 99; i++) {
    const change = (Math.random() - 0.42) * 200
    equity = Math.max(equity + change, 5000)
    equityCurve.push(Math.round(equity))
  }

  return {
    totalTrades,
    winTrades,
    lossTrades,
    winrate: (winTrades / totalTrades) * 100,
    profitFactor: 1.5 + Math.random() * 2,
    totalProfit: equity - 10000,
    maxDrawdown: 5 + Math.random() * 15,
    sharpeRatio: 1 + Math.random() * 2,
    equityCurve,
    trades: [],
  }
}

export default function BacktestPanel() {
  const { strategies } = useJarvisStore()
  const [strategyId, setStrategyId] = useState(strategies[0]?.id || 1)
  const [symbol, setSymbol] = useState('XAUUSD')
  const [timeframe, setTimeframe] = useState('H1')
  const [startDate, setStartDate] = useState('2024-01-01')
  const [endDate, setEndDate] = useState('2024-12-31')
  const [initialBalance, setInitialBalance] = useState('10000')
  const [isRunning, setIsRunning] = useState(false)
  const [result, setResult] = useState<BacktestResult | null>(null)
  const [progress, setProgress] = useState(0)

  const handleRunBacktest = async () => {
    setIsRunning(true)
    setResult(null)
    setProgress(0)

    const steps = [10, 25, 45, 62, 78, 90, 100]
    for (const step of steps) {
      await new Promise((r) => setTimeout(r, 300 + Math.random() * 200))
      setProgress(step)
    }

    await new Promise((r) => setTimeout(r, 400))
    const mockResult = generateMockBacktest()
    setResult(mockResult)
    setIsRunning(false)
    toast.success('Backtest completed!')
  }

  const equityCurveData = result?.equityCurve.map((v, i) => ({ day: i + 1, equity: v })) || []

  const tradeDistData = result
    ? [
        { name: 'Wins', value: result.winTrades, fill: '#00ff88' },
        { name: 'Losses', value: result.lossTrades, fill: '#ff3366' },
      ]
    : []

  return (
    <div className="p-6 space-y-6" style={{ backgroundColor: '#0a0a0f', minHeight: '100%' }}>
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-jarvis-text">Backtesting Engine</h1>
        <p className="text-xs text-jarvis-muted mt-0.5">Test strategies against historical data</p>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Configuration Panel */}
        <div
          className="rounded-xl p-5"
          style={{ backgroundColor: '#12121a', border: '1px solid #1e1e2e' }}
        >
          <div className="flex items-center gap-2 mb-4">
            <BarChart2 size={15} style={{ color: '#00d4ff' }} />
            <h2 className="text-sm font-semibold text-jarvis-text">Configuration</h2>
          </div>

          <div className="space-y-3">
            <div>
              <label className="text-[11px] text-jarvis-muted uppercase tracking-wider block mb-1.5">
                Strategy
              </label>
              <select
                value={strategyId}
                onChange={(e) => setStrategyId(Number(e.target.value))}
                className="jarvis-input"
                style={{ backgroundColor: 'rgba(30,30,46,0.6)' }}
              >
                {strategies.map((s) => (
                  <option key={s.id} value={s.id} style={{ backgroundColor: '#12121a' }}>
                    {s.name}
                  </option>
                ))}
              </select>
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="text-[11px] text-jarvis-muted uppercase tracking-wider block mb-1.5">
                  Symbol
                </label>
                <select
                  value={symbol}
                  onChange={(e) => setSymbol(e.target.value)}
                  className="jarvis-input"
                  style={{ backgroundColor: 'rgba(30,30,46,0.6)' }}
                >
                  {SYMBOLS.map((s) => (
                    <option key={s} value={s} style={{ backgroundColor: '#12121a' }}>{s}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-[11px] text-jarvis-muted uppercase tracking-wider block mb-1.5">
                  Timeframe
                </label>
                <select
                  value={timeframe}
                  onChange={(e) => setTimeframe(e.target.value)}
                  className="jarvis-input"
                  style={{ backgroundColor: 'rgba(30,30,46,0.6)' }}
                >
                  {TIMEFRAMES.map((tf) => (
                    <option key={tf} value={tf} style={{ backgroundColor: '#12121a' }}>{tf}</option>
                  ))}
                </select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="text-[11px] text-jarvis-muted uppercase tracking-wider block mb-1.5">
                  Start Date
                </label>
                <input
                  type="date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                  className="jarvis-input"
                />
              </div>
              <div>
                <label className="text-[11px] text-jarvis-muted uppercase tracking-wider block mb-1.5">
                  End Date
                </label>
                <input
                  type="date"
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                  className="jarvis-input"
                />
              </div>
            </div>

            <div>
              <label className="text-[11px] text-jarvis-muted uppercase tracking-wider block mb-1.5">
                Initial Balance ($)
              </label>
              <input
                type="number"
                value={initialBalance}
                onChange={(e) => setInitialBalance(e.target.value)}
                className="jarvis-input"
                placeholder="10000"
              />
            </div>

            {/* Progress Bar */}
            {isRunning && (
              <div>
                <div className="flex justify-between text-[11px] mb-1.5">
                  <span className="text-jarvis-muted">Processing...</span>
                  <span className="text-jarvis-accent font-mono">{progress}%</span>
                </div>
                <div
                  className="h-1.5 rounded-full overflow-hidden"
                  style={{ backgroundColor: 'rgba(30,30,46,0.8)' }}
                >
                  <div
                    className="h-full rounded-full transition-all duration-300"
                    style={{
                      width: `${progress}%`,
                      background: 'linear-gradient(90deg, #00d4ff, #8b5cf6)',
                    }}
                  />
                </div>
              </div>
            )}

            <button
              onClick={handleRunBacktest}
              disabled={isRunning}
              className="w-full flex items-center justify-center gap-2 py-3 rounded-xl font-bold text-sm transition-all disabled:opacity-60"
              style={{
                background: 'linear-gradient(135deg, rgba(0,212,255,0.2), rgba(139,92,246,0.2))',
                border: '1px solid rgba(0,212,255,0.3)',
                color: '#00d4ff',
              }}
            >
              {isRunning ? <Loader2 size={14} className="animate-spin" /> : <Play size={14} />}
              {isRunning ? 'Running Backtest...' : 'Run Backtest'}
            </button>
          </div>
        </div>

        {/* Results */}
        <div className="xl:col-span-2 space-y-4">
          {!result && !isRunning && (
            <div
              className="rounded-xl p-12 text-center"
              style={{ backgroundColor: '#12121a', border: '1px dashed rgba(30,30,46,0.8)' }}
            >
              <BarChart2 size={40} className="mx-auto mb-3 opacity-20" style={{ color: '#00d4ff' }} />
              <div className="text-jarvis-muted text-sm">Configure and run a backtest to see results</div>
            </div>
          )}

          {isRunning && (
            <div
              className="rounded-xl p-12 text-center"
              style={{ backgroundColor: '#12121a', border: '1px solid rgba(0,212,255,0.1)' }}
            >
              <div className="flex items-center justify-center gap-3 mb-4">
                <Loader2 size={20} className="animate-spin" style={{ color: '#00d4ff' }} />
                <span className="text-jarvis-accent font-semibold">Running backtest...</span>
              </div>
              <div className="text-xs text-jarvis-muted">
                Processing {symbol} {timeframe} from {startDate} to {endDate}
              </div>
            </div>
          )}

          {result && (
            <>
              {/* Key Metrics */}
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                {[
                  {
                    label: 'Winrate',
                    value: `${result.winrate.toFixed(1)}%`,
                    icon: <Target size={13} />,
                    color: result.winrate >= 60 ? '#00ff88' : result.winrate >= 50 ? '#ffcc00' : '#ff3366',
                    good: result.winrate >= 55,
                  },
                  {
                    label: 'Profit Factor',
                    value: result.profitFactor.toFixed(2),
                    icon: <Award size={13} />,
                    color: result.profitFactor >= 2 ? '#00ff88' : result.profitFactor >= 1.5 ? '#ffcc00' : '#ff3366',
                    good: result.profitFactor >= 1.5,
                  },
                  {
                    label: 'Max Drawdown',
                    value: `${result.maxDrawdown.toFixed(1)}%`,
                    icon: <TrendingDown size={13} />,
                    color: result.maxDrawdown <= 10 ? '#00ff88' : result.maxDrawdown <= 20 ? '#ffcc00' : '#ff3366',
                    good: result.maxDrawdown <= 15,
                  },
                  {
                    label: 'Sharpe Ratio',
                    value: result.sharpeRatio.toFixed(2),
                    icon: <TrendingUp size={13} />,
                    color: result.sharpeRatio >= 1.5 ? '#00ff88' : result.sharpeRatio >= 1 ? '#ffcc00' : '#ff3366',
                    good: result.sharpeRatio >= 1,
                  },
                ].map(({ label, value, icon, color, good }) => (
                  <div
                    key={label}
                    className="rounded-xl p-3 text-center"
                    style={{
                      backgroundColor: '#12121a',
                      border: `1px solid ${color}25`,
                    }}
                  >
                    <div className="flex items-center justify-center gap-1.5 mb-1.5">
                      <div style={{ color }}>{icon}</div>
                      {good ? (
                        <CheckCircle size={10} style={{ color: '#00ff88' }} />
                      ) : (
                        <XCircle size={10} style={{ color: '#ff3366' }} />
                      )}
                    </div>
                    <div className="text-lg font-bold font-mono" style={{ color }}>
                      {value}
                    </div>
                    <div className="text-[10px] text-jarvis-muted mt-0.5">{label}</div>
                  </div>
                ))}
              </div>

              {/* More stats */}
              <div
                className="rounded-xl p-4 grid grid-cols-3 gap-4"
                style={{ backgroundColor: '#12121a', border: '1px solid #1e1e2e' }}
              >
                {[
                  { label: 'Total Trades', value: String(result.totalTrades), color: '#00d4ff' },
                  { label: 'Win Trades', value: String(result.winTrades), color: '#00ff88' },
                  { label: 'Loss Trades', value: String(result.lossTrades), color: '#ff3366' },
                  { label: 'Net Profit', value: `${result.totalProfit >= 0 ? '+' : ''}$${result.totalProfit.toFixed(2)}`, color: result.totalProfit >= 0 ? '#00ff88' : '#ff3366' },
                  { label: 'Return %', value: `${((result.totalProfit / parseFloat(initialBalance)) * 100).toFixed(1)}%`, color: result.totalProfit >= 0 ? '#00ff88' : '#ff3366' },
                  { label: 'Period', value: `${startDate} – ${endDate}`, color: '#64748b' },
                ].map(({ label, value, color }) => (
                  <div key={label}>
                    <div className="text-[11px] text-jarvis-muted">{label}</div>
                    <div className="text-sm font-bold font-mono mt-0.5" style={{ color }}>
                      {value}
                    </div>
                  </div>
                ))}
              </div>

              {/* Equity Curve */}
              <div
                className="rounded-xl p-5"
                style={{ backgroundColor: '#12121a', border: '1px solid #1e1e2e' }}
              >
                <h3 className="text-sm font-semibold text-jarvis-text mb-4">Equity Curve</h3>
                <ResponsiveContainer width="100%" height={200}>
                  <AreaChart data={equityCurveData}>
                    <defs>
                      <linearGradient id="btGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor={result.totalProfit >= 0 ? '#00ff88' : '#ff3366'} stopOpacity={0.2} />
                        <stop offset="95%" stopColor={result.totalProfit >= 0 ? '#00ff88' : '#ff3366'} stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(30,30,46,0.8)" />
                    <XAxis
                      dataKey="day"
                      stroke="#64748b"
                      tick={{ fontSize: 10 }}
                      tickLine={false}
                      axisLine={false}
                    />
                    <YAxis
                      stroke="#64748b"
                      tick={{ fontSize: 10 }}
                      tickLine={false}
                      axisLine={false}
                      tickFormatter={(v) => `$${(v / 1000).toFixed(1)}k`}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#1a1a2e',
                        border: '1px solid rgba(0,212,255,0.2)',
                        borderRadius: '0.5rem',
                        fontSize: '0.75rem',
                        fontFamily: 'JetBrains Mono',
                      }}
                    />
                    <Area
                      type="monotone"
                      dataKey="equity"
                      stroke={result.totalProfit >= 0 ? '#00ff88' : '#ff3366'}
                      strokeWidth={2}
                      fill="url(#btGrad)"
                      dot={false}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
