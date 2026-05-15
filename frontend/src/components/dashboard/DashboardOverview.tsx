'use client'

import { useJarvisStore } from '@/store/useJarvisStore'
import StatCard from './StatCard'
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import {
  DollarSign,
  TrendingUp,
  TrendingDown,
  Target,
  Activity,
  AlertTriangle,
  Cpu,
  Circle,
  ArrowUpRight,
  ArrowDownRight,
} from 'lucide-react'
import { format, parseISO } from 'date-fns'
import clsx from 'clsx'

const CustomTooltip = ({ active, payload, label }: {
  active?: boolean
  payload?: { value: number }[]
  label?: string
}) => {
  if (active && payload && payload.length) {
    return (
      <div
        className="px-3 py-2 rounded-lg text-xs font-mono"
        style={{
          backgroundColor: '#1a1a2e',
          border: '1px solid rgba(0,212,255,0.2)',
          boxShadow: '0 0 12px rgba(0,212,255,0.1)',
        }}
      >
        <div className="text-jarvis-muted mb-0.5">{label}</div>
        <div className="text-jarvis-accent font-semibold">
          ${payload[0].value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
        </div>
      </div>
    )
  }
  return null
}

export default function DashboardOverview() {
  const { dashboardData, openTrades, strategies, connectionStatus, accountInfo } = useJarvisStore()

  const profitPositive = dashboardData.profit >= 0
  const activeStrategies = strategies.filter((s) => s.status === 'ACTIVE')

  return (
    <div className="p-6 space-y-6 min-h-full" style={{ backgroundColor: '#0a0a0f' }}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-jarvis-text tracking-wide">
            Trading Dashboard
          </h1>
          <p className="text-xs text-jarvis-muted mt-0.5">
            Live account overview • {new Date().toLocaleString()}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5">
            <div className="relative w-2 h-2">
              <div className="w-2 h-2 rounded-full bg-jarvis-green" />
              <div className="absolute inset-0 rounded-full bg-jarvis-green opacity-40 animate-ping" />
            </div>
            <span className="text-xs text-jarvis-green font-semibold">LIVE</span>
          </div>
          <div
            className="px-3 py-1.5 rounded-lg text-xs font-mono"
            style={{
              backgroundColor: 'rgba(0,212,255,0.08)',
              border: '1px solid rgba(0,212,255,0.2)',
              color: '#00d4ff',
            }}
          >
            {accountInfo.currency} Account
          </div>
        </div>
      </div>

      {/* Stat Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
        <StatCard
          title="Balance"
          value={`$${dashboardData.balance.toLocaleString('en-US', { minimumFractionDigits: 2 })}`}
          icon={<DollarSign size={16} />}
          variant="accent"
          subtitle="Account balance"
          animated
        />
        <StatCard
          title="Equity"
          value={`$${dashboardData.equity.toLocaleString('en-US', { minimumFractionDigits: 2 })}`}
          icon={<Activity size={16} />}
          variant="accent"
          subtitle="Real-time equity"
          animated
        />
        <StatCard
          title="Profit / Loss"
          value={`${profitPositive ? '+' : ''}$${dashboardData.profit.toFixed(2)}`}
          icon={profitPositive ? <TrendingUp size={16} /> : <TrendingDown size={16} />}
          variant={profitPositive ? 'positive' : 'negative'}
          change={dashboardData.balance > 0 ? (dashboardData.profit / dashboardData.balance) * 100 : 0}
          changeLabel="vs balance"
          animated
        />
        <StatCard
          title="Winrate"
          value={`${dashboardData.winrate.toFixed(1)}%`}
          icon={<Target size={16} />}
          variant={dashboardData.winrate >= 60 ? 'positive' : dashboardData.winrate >= 50 ? 'warning' : 'negative'}
          subtitle="All strategies"
        />
        <StatCard
          title="Open Trades"
          value={String(dashboardData.openTrades)}
          icon={<Circle size={16} />}
          variant="default"
          subtitle={`${openTrades.filter((t) => t.profit > 0).length} profitable`}
        />
        <StatCard
          title="Drawdown"
          value={`${dashboardData.drawdown.toFixed(1)}%`}
          icon={<AlertTriangle size={16} />}
          variant={dashboardData.drawdown <= 5 ? 'positive' : dashboardData.drawdown <= 10 ? 'warning' : 'negative'}
          subtitle="Current drawdown"
        />
      </div>

      {/* Charts + Right Panel */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Equity Curve */}
        <div
          className="xl:col-span-2 rounded-xl p-5"
          style={{
            backgroundColor: '#12121a',
            border: '1px solid #1e1e2e',
          }}
        >
          <div className="flex items-center justify-between mb-5">
            <div>
              <h2 className="text-sm font-semibold text-jarvis-text">Equity Curve</h2>
              <p className="text-[11px] text-jarvis-muted mt-0.5">30-day performance</p>
            </div>
            <div className="flex gap-2">
              {['1D', '1W', '1M', '3M'].map((period) => (
                <button
                  key={period}
                  className={clsx(
                    'px-2.5 py-1 rounded text-[11px] font-semibold transition-all',
                    period === '1M'
                      ? 'text-jarvis-accent'
                      : 'text-jarvis-muted hover:text-jarvis-text'
                  )}
                  style={period === '1M' ? {
                    backgroundColor: 'rgba(0,212,255,0.1)',
                    border: '1px solid rgba(0,212,255,0.2)',
                  } : {
                    backgroundColor: 'rgba(30,30,46,0.4)',
                    border: '1px solid transparent',
                  }}
                >
                  {period}
                </button>
              ))}
            </div>
          </div>
          <ResponsiveContainer width="100%" height={200}>
            <AreaChart data={dashboardData.equityCurve}>
              <defs>
                <linearGradient id="equityGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#00d4ff" stopOpacity={0.2} />
                  <stop offset="95%" stopColor="#00d4ff" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(30,30,46,0.8)" />
              <XAxis
                dataKey="time"
                stroke="#64748b"
                tick={{ fontSize: 10, fontFamily: 'JetBrains Mono' }}
                tickLine={false}
                axisLine={false}
                interval="preserveStartEnd"
              />
              <YAxis
                stroke="#64748b"
                tick={{ fontSize: 10, fontFamily: 'JetBrains Mono' }}
                tickLine={false}
                axisLine={false}
                tickFormatter={(v) => `$${(v / 1000).toFixed(1)}k`}
              />
              <Tooltip content={<CustomTooltip />} />
              <Area
                type="monotone"
                dataKey="value"
                stroke="#00d4ff"
                strokeWidth={2}
                fill="url(#equityGrad)"
                dot={false}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Right Panel: AI + Active Strategies */}
        <div className="flex flex-col gap-4">
          {/* AI Status Panel */}
          <div
            className="rounded-xl p-4"
            style={{
              backgroundColor: '#12121a',
              border: '1px solid rgba(139,92,246,0.2)',
              boxShadow: '0 0 12px rgba(139,92,246,0.05)',
            }}
          >
            <div className="flex items-center gap-2.5 mb-3">
              <div
                className="flex items-center justify-center w-8 h-8 rounded-lg"
                style={{
                  background: 'linear-gradient(135deg, rgba(139,92,246,0.2), rgba(0,212,255,0.2))',
                  border: '1px solid rgba(139,92,246,0.3)',
                }}
              >
                <Cpu size={14} style={{ color: '#8b5cf6' }} />
              </div>
              <div>
                <div className="text-xs font-semibold text-jarvis-text">JARVIS AI</div>
                <div className="text-[10px] text-jarvis-green flex items-center gap-1">
                  <div className="w-1.5 h-1.5 rounded-full bg-jarvis-green animate-pulse" />
                  Online & Ready
                </div>
              </div>
            </div>
            <div className="space-y-2">
              {[
                { label: 'Model', value: 'GPT-4 Turbo' },
                { label: 'Mode', value: 'Trading Expert' },
                { label: 'Context', value: '128K tokens' },
              ].map(({ label, value }) => (
                <div key={label} className="flex justify-between items-center text-[11px]">
                  <span className="text-jarvis-muted">{label}</span>
                  <span
                    className="font-semibold"
                    style={{ color: '#8b5cf6' }}
                  >
                    {value}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Active Strategies */}
          <div
            className="rounded-xl p-4 flex-1"
            style={{
              backgroundColor: '#12121a',
              border: '1px solid #1e1e2e',
            }}
          >
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-xs font-semibold text-jarvis-text">Active Strategies</h3>
              <span
                className="text-[10px] px-2 py-0.5 rounded-full font-semibold"
                style={{
                  backgroundColor: 'rgba(0,255,136,0.1)',
                  color: '#00ff88',
                  border: '1px solid rgba(0,255,136,0.2)',
                }}
              >
                {activeStrategies.length} running
              </span>
            </div>
            <div className="space-y-2.5">
              {activeStrategies.slice(0, 3).map((strategy) => (
                <div
                  key={strategy.id}
                  className="rounded-lg p-2.5 group"
                  style={{
                    backgroundColor: 'rgba(30,30,46,0.4)',
                    border: '1px solid rgba(30,30,46,0.8)',
                  }}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-[11px] font-semibold text-jarvis-text truncate max-w-[120px]">
                      {strategy.name}
                    </span>
                    <span
                      className="text-[10px] font-bold"
                      style={{ color: '#00ff88' }}
                    >
                      {strategy.winrate.toFixed(1)}%
                    </span>
                  </div>
                  <div className="flex items-center justify-between text-[10px] text-jarvis-muted">
                    <span>{strategy.type}</span>
                    <span>PF: {strategy.profitFactor.toFixed(2)}</span>
                  </div>
                  {/* Progress bar */}
                  <div
                    className="mt-1.5 rounded-full overflow-hidden"
                    style={{ height: '2px', backgroundColor: 'rgba(30,30,46,0.8)' }}
                  >
                    <div
                      className="h-full rounded-full"
                      style={{
                        width: `${strategy.winrate}%`,
                        background: 'linear-gradient(90deg, #00ff88, #00d4ff)',
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Bottom Row: Recent Trades + Market Analysis */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        {/* Recent Trades */}
        <div
          className="rounded-xl overflow-hidden"
          style={{
            backgroundColor: '#12121a',
            border: '1px solid #1e1e2e',
          }}
        >
          <div
            className="flex items-center justify-between px-5 py-4 border-b"
            style={{ borderColor: '#1e1e2e' }}
          >
            <h2 className="text-sm font-semibold text-jarvis-text">Open Trades</h2>
            <span className="text-[11px] text-jarvis-muted">{openTrades.length} positions</span>
          </div>
          <div className="overflow-x-auto">
            <table className="jarvis-table">
              <thead>
                <tr>
                  <th>Symbol</th>
                  <th>Type</th>
                  <th>Lots</th>
                  <th>P&amp;L</th>
                </tr>
              </thead>
              <tbody>
                {openTrades.map((trade) => (
                  <tr key={trade.ticket}>
                    <td className="font-semibold text-jarvis-text">{trade.symbol}</td>
                    <td>
                      <span
                        className={clsx(
                          'inline-flex items-center gap-0.5 px-2 py-0.5 rounded text-[10px] font-bold'
                        )}
                        style={{
                          backgroundColor: trade.type === 'BUY'
                            ? 'rgba(0,255,136,0.1)'
                            : 'rgba(255,51,102,0.1)',
                          color: trade.type === 'BUY' ? '#00ff88' : '#ff3366',
                        }}
                      >
                        {trade.type === 'BUY' ? (
                          <ArrowUpRight size={10} />
                        ) : (
                          <ArrowDownRight size={10} />
                        )}
                        {trade.type}
                      </span>
                    </td>
                    <td className="text-jarvis-muted">{trade.lots}</td>
                    <td
                      className="font-semibold"
                      style={{ color: trade.profit >= 0 ? '#00ff88' : '#ff3366' }}
                    >
                      {trade.profit >= 0 ? '+' : ''}${trade.profit.toFixed(2)}
                    </td>
                  </tr>
                ))}
                {openTrades.length === 0 && (
                  <tr>
                    <td colSpan={4} className="text-center text-jarvis-muted py-6 text-xs">
                      No open trades
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Market Analysis */}
        <div
          className="rounded-xl p-5"
          style={{
            backgroundColor: '#12121a',
            border: '1px solid #1e1e2e',
          }}
        >
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-jarvis-text">Market Analysis</h2>
            <span className="text-[10px] text-jarvis-muted">AI-powered</span>
          </div>
          <div className="space-y-3">
            {[
              { symbol: 'XAUUSD', bias: 'BULLISH', strength: 78, price: '2,318.50', change: +0.82 },
              { symbol: 'EURUSD', bias: 'BEARISH', strength: 62, price: '1.0832', change: -0.31 },
              { symbol: 'GBPUSD', bias: 'NEUTRAL', strength: 45, price: '1.2665', change: +0.12 },
              { symbol: 'USDJPY', bias: 'BULLISH', strength: 71, price: '154.85', change: +0.47 },
            ].map(({ symbol, bias, strength, price, change }) => (
              <div
                key={symbol}
                className="flex items-center gap-3 p-3 rounded-lg"
                style={{
                  backgroundColor: 'rgba(30,30,46,0.4)',
                  border: '1px solid rgba(30,30,46,0.8)',
                }}
              >
                <div className="w-14 text-xs font-bold text-jarvis-text">{symbol}</div>
                <div className="flex-1">
                  <div
                    className="h-1.5 rounded-full overflow-hidden"
                    style={{ backgroundColor: 'rgba(30,30,46,0.8)' }}
                  >
                    <div
                      className="h-full rounded-full"
                      style={{
                        width: `${strength}%`,
                        backgroundColor:
                          bias === 'BULLISH'
                            ? '#00ff88'
                            : bias === 'BEARISH'
                            ? '#ff3366'
                            : '#ffcc00',
                      }}
                    />
                  </div>
                </div>
                <span
                  className="text-[10px] font-bold w-14 text-center"
                  style={{
                    color:
                      bias === 'BULLISH'
                        ? '#00ff88'
                        : bias === 'BEARISH'
                        ? '#ff3366'
                        : '#ffcc00',
                  }}
                >
                  {bias}
                </span>
                <div className="text-right">
                  <div className="text-[11px] font-mono font-semibold text-jarvis-text">{price}</div>
                  <div
                    className="text-[10px]"
                    style={{ color: change >= 0 ? '#00ff88' : '#ff3366' }}
                  >
                    {change >= 0 ? '+' : ''}{change}%
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
