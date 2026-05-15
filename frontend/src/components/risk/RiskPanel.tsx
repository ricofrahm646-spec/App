'use client'

import { useState } from 'react'
import { useJarvisStore } from '@/store/useJarvisStore'
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  RadialBarChart,
  RadialBar,
  Tooltip,
} from 'recharts'
import {
  Shield,
  AlertTriangle,
  TrendingDown,
  TrendingUp,
  DollarSign,
  Percent,
  Loader2,
  CheckCircle,
  XCircle,
} from 'lucide-react'
import toast from 'react-hot-toast'
import clsx from 'clsx'

function DrawdownGauge({ value, max = 20 }: { value: number; max?: number }) {
  const percent = Math.min((value / max) * 100, 100)
  const color = value <= 5 ? '#00ff88' : value <= 10 ? '#ffcc00' : '#ff3366'

  const data = [
    { value: percent, fill: color },
    { value: 100 - percent, fill: 'rgba(30,30,46,0.4)' },
  ]

  return (
    <div className="relative flex flex-col items-center">
      <ResponsiveContainer width={160} height={160}>
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            startAngle={180}
            endAngle={0}
            innerRadius={55}
            outerRadius={75}
            dataKey="value"
            strokeWidth={0}
          >
            {data.map((entry, index) => (
              <Cell key={index} fill={entry.fill} />
            ))}
          </Pie>
        </PieChart>
      </ResponsiveContainer>
      <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/4 text-center">
        <div className="text-2xl font-bold font-mono" style={{ color }}>
          {value.toFixed(1)}%
        </div>
        <div className="text-[11px] text-jarvis-muted">Drawdown</div>
      </div>
    </div>
  )
}

export default function RiskPanel() {
  const { riskMetrics, accountInfo } = useJarvisStore()
  const [riskPerTrade, setRiskPerTrade] = useState('1.0')
  const [maxDailyLoss, setMaxDailyLoss] = useState('3.0')
  const [maxDrawdown, setMaxDrawdown] = useState('10.0')
  const [maxPositions, setMaxPositions] = useState('3')
  const [isSaving, setIsSaving] = useState(false)
  const [stopTrading, setStopTrading] = useState(false)

  // Position Calculator
  const [calcSymbol, setCalcSymbol] = useState('XAUUSD')
  const [calcBalance, setCalcBalance] = useState(String(accountInfo.balance.toFixed(2)))
  const [calcRisk, setCalcRisk] = useState('1.0')
  const [calcSlPips, setCalcSlPips] = useState('50')

  const calcLots = () => {
    const risk = parseFloat(calcRisk) / 100
    const balance = parseFloat(calcBalance)
    const pips = parseFloat(calcSlPips)
    if (!pips || pips === 0 || !balance) return '0.00'
    const riskAmt = balance * risk
    const lots = riskAmt / (pips * 10)
    return Math.min(lots, 100).toFixed(2)
  }

  const handleSave = async () => {
    setIsSaving(true)
    await new Promise((r) => setTimeout(r, 800))
    setIsSaving(false)
    toast.success('Risk settings saved!')
  }

  const handleEmergencyStop = () => {
    setStopTrading(true)
    toast.error('Trading halted - Emergency stop activated', { duration: 5000 })
  }

  const handleResumeTrading = () => {
    setStopTrading(false)
    toast.success('Trading resumed')
  }

  const riskScore = Math.max(0, 100 - riskMetrics.currentDrawdown * 5)
  const riskLevel = riskScore >= 80 ? 'LOW' : riskScore >= 60 ? 'MEDIUM' : 'HIGH'
  const riskColor = riskScore >= 80 ? '#00ff88' : riskScore >= 60 ? '#ffcc00' : '#ff3366'

  return (
    <div className="p-6 space-y-6" style={{ backgroundColor: '#0a0a0f', minHeight: '100%' }}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-jarvis-text">Risk Manager</h1>
          <p className="text-xs text-jarvis-muted mt-0.5">
            Real-time risk monitoring and position management
          </p>
        </div>

        {stopTrading ? (
          <button
            onClick={handleResumeTrading}
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl font-bold text-sm transition-all"
            style={{
              background: 'rgba(0,255,136,0.15)',
              border: '1px solid rgba(0,255,136,0.4)',
              color: '#00ff88',
            }}
          >
            <CheckCircle size={15} />
            Resume Trading
          </button>
        ) : (
          <button
            onClick={handleEmergencyStop}
            className="flex items-center gap-2 px-4 py-2.5 rounded-xl font-bold text-sm transition-all"
            style={{
              background: 'linear-gradient(135deg, rgba(255,51,102,0.25), rgba(255,51,102,0.15))',
              border: '2px solid rgba(255,51,102,0.5)',
              color: '#ff3366',
              boxShadow: '0 0 15px rgba(255,51,102,0.15)',
            }}
          >
            <AlertTriangle size={15} />
            EMERGENCY STOP
          </button>
        )}
      </div>

      {/* Stop Trading Banner */}
      {stopTrading && (
        <div
          className="flex items-center gap-3 px-5 py-4 rounded-xl animate-pulse-slow"
          style={{
            background: 'linear-gradient(90deg, rgba(255,51,102,0.1), rgba(255,51,102,0.05))',
            border: '1px solid rgba(255,51,102,0.4)',
          }}
        >
          <AlertTriangle size={18} style={{ color: '#ff3366' }} />
          <div>
            <div className="text-sm font-bold text-jarvis-red">Trading Halted</div>
            <div className="text-xs text-jarvis-muted">Emergency stop is active. No new orders will be placed.</div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Drawdown Gauge + Risk Score */}
        <div
          className="rounded-xl p-5 flex flex-col items-center"
          style={{ backgroundColor: '#12121a', border: '1px solid #1e1e2e' }}
        >
          <h2 className="text-sm font-semibold text-jarvis-text mb-4 self-start">Risk Overview</h2>
          <DrawdownGauge value={riskMetrics.currentDrawdown} />

          <div className="w-full mt-4 space-y-2.5">
            {[
              { label: 'Current DD', value: `${riskMetrics.currentDrawdown.toFixed(1)}%`, color: riskMetrics.currentDrawdown <= 5 ? '#00ff88' : '#ffcc00' },
              { label: 'Max DD', value: `${riskMetrics.maxDrawdown.toFixed(1)}%`, color: '#ff3366' },
              { label: 'Daily P&L', value: `+$${riskMetrics.dailyPnL.toFixed(2)}`, color: '#00ff88' },
            ].map(({ label, value, color }) => (
              <div key={label} className="flex justify-between items-center text-xs">
                <span className="text-jarvis-muted">{label}</span>
                <span className="font-mono font-bold" style={{ color }}>{value}</span>
              </div>
            ))}
          </div>

          <div
            className="w-full mt-4 rounded-lg p-3 text-center"
            style={{
              backgroundColor: `${riskColor}10`,
              border: `1px solid ${riskColor}25`,
            }}
          >
            <div className="text-[11px] text-jarvis-muted mb-1">Risk Level</div>
            <div className="text-lg font-bold" style={{ color: riskColor }}>
              {riskLevel}
            </div>
            <div className="text-[10px]" style={{ color: riskColor }}>
              Score: {riskScore.toFixed(0)}/100
            </div>
          </div>
        </div>

        {/* Risk Settings */}
        <div
          className="rounded-xl p-5"
          style={{ backgroundColor: '#12121a', border: '1px solid #1e1e2e' }}
        >
          <div className="flex items-center gap-2 mb-4">
            <Shield size={14} style={{ color: '#8b5cf6' }} />
            <h2 className="text-sm font-semibold text-jarvis-text">Risk Settings</h2>
          </div>

          <div className="space-y-4">
            <div>
              <div className="flex justify-between text-[11px] mb-1.5">
                <label className="text-jarvis-muted uppercase tracking-wider">Risk Per Trade</label>
                <span className="text-jarvis-purple font-bold">{riskPerTrade}%</span>
              </div>
              <input
                type="range" min="0.1" max="5" step="0.1"
                value={riskPerTrade}
                onChange={(e) => setRiskPerTrade(e.target.value)}
                className="w-full accent-purple-500"
              />
              <div className="flex justify-between text-[10px] text-jarvis-muted mt-0.5">
                <span>0.1%</span><span>5%</span>
              </div>
            </div>

            <div>
              <div className="flex justify-between text-[11px] mb-1.5">
                <label className="text-jarvis-muted uppercase tracking-wider">Max Daily Loss</label>
                <span className="text-jarvis-red font-bold">{maxDailyLoss}%</span>
              </div>
              <input
                type="range" min="1" max="10" step="0.5"
                value={maxDailyLoss}
                onChange={(e) => setMaxDailyLoss(e.target.value)}
                className="w-full accent-red-500"
              />
            </div>

            <div>
              <div className="flex justify-between text-[11px] mb-1.5">
                <label className="text-jarvis-muted uppercase tracking-wider">Max Drawdown</label>
                <span className="text-jarvis-yellow font-bold">{maxDrawdown}%</span>
              </div>
              <input
                type="range" min="5" max="30" step="1"
                value={maxDrawdown}
                onChange={(e) => setMaxDrawdown(e.target.value)}
                className="w-full accent-yellow-500"
              />
            </div>

            <div>
              <label className="text-[11px] text-jarvis-muted uppercase tracking-wider block mb-1.5">
                Max Open Positions
              </label>
              <div className="flex gap-2">
                {[1, 2, 3, 5, 10].map((n) => (
                  <button
                    key={n}
                    onClick={() => setMaxPositions(String(n))}
                    className="flex-1 py-2 rounded-lg text-xs font-bold transition-all"
                    style={maxPositions === String(n) ? {
                      backgroundColor: 'rgba(0,212,255,0.15)',
                      border: '1px solid rgba(0,212,255,0.3)',
                      color: '#00d4ff',
                    } : {
                      backgroundColor: 'rgba(30,30,46,0.4)',
                      border: '1px solid rgba(30,30,46,0.8)',
                      color: '#64748b',
                    }}
                  >
                    {n}
                  </button>
                ))}
              </div>
            </div>

            <button
              onClick={handleSave}
              disabled={isSaving}
              className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl text-sm font-semibold transition-all"
              style={{
                background: 'linear-gradient(135deg, rgba(139,92,246,0.2), rgba(0,212,255,0.1))',
                border: '1px solid rgba(139,92,246,0.3)',
                color: '#8b5cf6',
              }}
            >
              {isSaving ? <Loader2 size={13} className="animate-spin" /> : <Shield size={13} />}
              {isSaving ? 'Saving...' : 'Save Settings'}
            </button>
          </div>
        </div>

        {/* Position Size Calculator */}
        <div
          className="rounded-xl p-5"
          style={{ backgroundColor: '#12121a', border: '1px solid #1e1e2e' }}
        >
          <div className="flex items-center gap-2 mb-4">
            <DollarSign size={14} style={{ color: '#00ff88' }} />
            <h2 className="text-sm font-semibold text-jarvis-text">Position Calculator</h2>
          </div>

          <div className="space-y-3">
            <div>
              <label className="text-[11px] text-jarvis-muted uppercase tracking-wider block mb-1.5">
                Symbol
              </label>
              <select
                value={calcSymbol}
                onChange={(e) => setCalcSymbol(e.target.value)}
                className="jarvis-input"
                style={{ backgroundColor: 'rgba(30,30,46,0.6)' }}
              >
                {['XAUUSD', 'EURUSD', 'GBPUSD', 'USDJPY', 'BTCUSD'].map((s) => (
                  <option key={s} value={s} style={{ backgroundColor: '#12121a' }}>{s}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="text-[11px] text-jarvis-muted uppercase tracking-wider block mb-1.5">
                Account Balance ($)
              </label>
              <input
                type="number"
                value={calcBalance}
                onChange={(e) => setCalcBalance(e.target.value)}
                className="jarvis-input"
              />
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="text-[11px] text-jarvis-muted uppercase tracking-wider block mb-1.5">
                  Risk (%)
                </label>
                <input
                  type="number"
                  value={calcRisk}
                  onChange={(e) => setCalcRisk(e.target.value)}
                  step="0.1"
                  className="jarvis-input"
                />
              </div>
              <div>
                <label className="text-[11px] text-jarvis-muted uppercase tracking-wider block mb-1.5">
                  SL (Pips)
                </label>
                <input
                  type="number"
                  value={calcSlPips}
                  onChange={(e) => setCalcSlPips(e.target.value)}
                  className="jarvis-input"
                />
              </div>
            </div>

            {/* Results */}
            <div
              className="rounded-xl p-4 space-y-3"
              style={{
                background: 'linear-gradient(135deg, rgba(0,255,136,0.05), rgba(0,212,255,0.05))',
                border: '1px solid rgba(0,255,136,0.15)',
              }}
            >
              <div className="text-[11px] text-jarvis-muted uppercase tracking-wider">Results</div>
              {[
                {
                  label: 'Lot Size',
                  value: `${calcLots()} lots`,
                  color: '#00d4ff',
                  big: true,
                },
                {
                  label: 'Risk Amount',
                  value: `$${(parseFloat(calcBalance || '0') * parseFloat(calcRisk || '0') / 100).toFixed(2)}`,
                  color: '#ffcc00',
                },
                {
                  label: 'Max Loss',
                  value: `-$${(parseFloat(calcBalance || '0') * parseFloat(calcRisk || '0') / 100).toFixed(2)}`,
                  color: '#ff3366',
                },
              ].map(({ label, value, color, big }) => (
                <div key={label} className="flex justify-between items-center">
                  <span className="text-[11px] text-jarvis-muted">{label}</span>
                  <span
                    className={`font-mono font-bold ${big ? 'text-base' : 'text-xs'}`}
                    style={{ color }}
                  >
                    {value}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Risk Metrics Grid */}
      <div
        className="rounded-xl p-5"
        style={{ backgroundColor: '#12121a', border: '1px solid #1e1e2e' }}
      >
        <h2 className="text-sm font-semibold text-jarvis-text mb-4">Live Risk Metrics</h2>
        <div className="grid grid-cols-2 lg:grid-cols-4 xl:grid-cols-6 gap-4">
          {[
            { label: 'Account Balance', value: `$${accountInfo.balance.toLocaleString()}`, color: '#00d4ff' },
            { label: 'Account Equity', value: `$${accountInfo.equity.toLocaleString()}`, color: '#00d4ff' },
            { label: 'Current DD', value: `${riskMetrics.currentDrawdown.toFixed(2)}%`, color: riskMetrics.currentDrawdown <= 5 ? '#00ff88' : '#ffcc00' },
            { label: 'Max DD', value: `${riskMetrics.maxDrawdown.toFixed(2)}%`, color: '#ff3366' },
            { label: 'Daily P&L', value: `+$${riskMetrics.dailyPnL.toFixed(2)}`, color: '#00ff88' },
            { label: 'Margin Level', value: `${accountInfo.marginLevel.toFixed(0)}%`, color: accountInfo.marginLevel > 200 ? '#00ff88' : '#ffcc00' },
          ].map(({ label, value, color }) => (
            <div
              key={label}
              className="rounded-lg p-3"
              style={{ backgroundColor: 'rgba(30,30,46,0.4)', border: '1px solid rgba(30,30,46,0.8)' }}
            >
              <div className="text-[10px] text-jarvis-muted mb-1">{label}</div>
              <div className="text-sm font-bold font-mono" style={{ color }}>{value}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
