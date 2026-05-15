'use client'

import { useState } from 'react'
import { useJarvisStore } from '@/store/useJarvisStore'
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
  Activity,
  Copy,
  Check,
  RefreshCw,
  Code,
  Webhook,
  ArrowUpRight,
  ArrowDownRight,
  Eye,
  EyeOff,
  Loader2,
  Zap,
} from 'lucide-react'
import toast from 'react-hot-toast'
import { format, parseISO } from 'date-fns'
import clsx from 'clsx'

const PINE_SCRIPT_TEMPLATE = `//@version=5
strategy("JARVIS Webhook Strategy", overlay=true, 
         default_qty_type=strategy.percent_of_equity, 
         default_qty_value=1)

// JARVIS Webhook URL Configuration
// Update with your webhook URL in alerts
var string WEBHOOK_URL = "https://your-jarvis-url.com/api/tradingview/webhook"

// Parameters
ema_fast = input.int(20, "Fast EMA")
ema_slow = input.int(50, "Slow EMA")  
rsi_len  = input.int(14, "RSI Length")
rsi_ob   = input.int(70, "RSI Overbought")
rsi_os   = input.int(30, "RSI Oversold")

// Indicators
ema_f = ta.ema(close, ema_fast)
ema_s = ta.ema(close, ema_slow)
rsi   = ta.rsi(close, rsi_len)
atr   = ta.atr(14)

// Signals
long_signal  = ta.crossover(ema_f, ema_s) and rsi < rsi_ob
short_signal = ta.crossunder(ema_f, ema_s) and rsi > rsi_os

// Plot EMAs
plot(ema_f, "Fast EMA", color=color.new(#00d4ff, 0), linewidth=2)
plot(ema_s, "Slow EMA", color=color.new(#8b5cf6, 0), linewidth=2)

// Strategy Entries
if long_signal
    strategy.entry("Long", strategy.long)
    alert('{"action":"BUY","symbol":"' + syminfo.ticker + '","price":' + str.tostring(close) + ',"sl":' + str.tostring(close - atr * 2) + ',"tp":' + str.tostring(close + atr * 3) + ',"strategy":"JARVIS_TV"}', alert.freq_once_per_bar)

if short_signal
    strategy.entry("Short", strategy.short)
    alert('{"action":"SELL","symbol":"' + syminfo.ticker + '","price":' + str.tostring(close) + ',"sl":' + str.tostring(close + atr * 2) + ',"tp":' + str.tostring(close - atr * 3) + ',"strategy":"JARVIS_TV"}', alert.freq_once_per_bar)

// Visual signals
plotshape(long_signal,  "Buy",  shape.triangleup,   location.belowbar, color.new(#00ff88, 0), size=size.small)
plotshape(short_signal, "Sell", shape.triangledown, location.abovebar, color.new(#ff3366, 0), size=size.small)`

const signalChartData = Array.from({ length: 20 }, (_, i) => ({
  day: i + 1,
  signals: Math.floor(Math.random() * 8) + 1,
  processed: Math.floor(Math.random() * 7) + 1,
}))

export default function TradingViewPanel() {
  const { tradingViewSignals } = useJarvisStore()
  const [webhookSecret, setWebhookSecret] = useState('jarvis_secret_2024')
  const [showSecret, setShowSecret] = useState(false)
  const [copiedUrl, setCopiedUrl] = useState(false)
  const [copiedScript, setCopiedScript] = useState(false)
  const [isRegenerating, setIsRegenerating] = useState(false)
  const [activeTab, setActiveTab] = useState<'signals' | 'pinescript'>('signals')

  const webhookUrl = 'https://jarvis.yourdomain.com/api/tradingview/webhook'

  const handleCopyUrl = () => {
    navigator.clipboard.writeText(webhookUrl)
    setCopiedUrl(true)
    setTimeout(() => setCopiedUrl(false), 2000)
    toast.success('Webhook URL copied!')
  }

  const handleCopyScript = () => {
    navigator.clipboard.writeText(PINE_SCRIPT_TEMPLATE)
    setCopiedScript(true)
    setTimeout(() => setCopiedScript(false), 2000)
    toast.success('Pine Script copied!')
  }

  const handleRegenerateSecret = async () => {
    setIsRegenerating(true)
    await new Promise((r) => setTimeout(r, 800))
    const newSecret = 'jarvis_' + Math.random().toString(36).substr(2, 16)
    setWebhookSecret(newSecret)
    setIsRegenerating(false)
    toast.success('Webhook secret regenerated!')
  }

  const processedCount = tradingViewSignals.filter((s) => s.processed).length

  return (
    <div className="p-6 space-y-6" style={{ backgroundColor: '#0a0a0f', minHeight: '100%' }}>
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-jarvis-text">TradingView Integration</h1>
        <p className="text-xs text-jarvis-muted mt-0.5">
          Webhook receiver for Pine Script alerts
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: 'Total Signals', value: String(tradingViewSignals.length), color: '#00d4ff' },
          { label: 'Processed', value: String(processedCount), color: '#00ff88' },
          { label: 'Pending', value: String(tradingViewSignals.length - processedCount), color: '#ffcc00' },
          { label: 'Success Rate', value: tradingViewSignals.length > 0 ? `${((processedCount / tradingViewSignals.length) * 100).toFixed(0)}%` : '0%', color: '#8b5cf6' },
        ].map(({ label, value, color }) => (
          <div
            key={label}
            className="rounded-xl p-4"
            style={{ backgroundColor: '#12121a', border: '1px solid rgba(30,30,46,0.8)' }}
          >
            <div className="text-[11px] text-jarvis-muted uppercase tracking-wider mb-1">{label}</div>
            <div className="text-2xl font-bold font-mono" style={{ color }}>{value}</div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-5 gap-6">
        {/* Webhook Config */}
        <div
          className="xl:col-span-2 space-y-4"
        >
          {/* Webhook URL */}
          <div
            className="rounded-xl p-5"
            style={{ backgroundColor: '#12121a', border: '1px solid #1e1e2e' }}
          >
            <div className="flex items-center gap-2 mb-4">
              <Webhook size={14} style={{ color: '#00d4ff' }} />
              <h2 className="text-sm font-semibold text-jarvis-text">Webhook URL</h2>
            </div>
            <div
              className="flex items-center gap-2 p-3 rounded-lg mb-3"
              style={{ backgroundColor: 'rgba(0,212,255,0.05)', border: '1px solid rgba(0,212,255,0.15)' }}
            >
              <span className="text-[11px] font-mono text-jarvis-accent flex-1 truncate">
                {webhookUrl}
              </span>
              <button
                onClick={handleCopyUrl}
                className="flex-shrink-0 text-jarvis-muted hover:text-jarvis-accent transition-colors"
              >
                {copiedUrl ? <Check size={13} /> : <Copy size={13} />}
              </button>
            </div>
            <p className="text-[11px] text-jarvis-muted">
              Use this URL in TradingView alert webhook field
            </p>
          </div>

          {/* Webhook Secret */}
          <div
            className="rounded-xl p-5"
            style={{ backgroundColor: '#12121a', border: '1px solid #1e1e2e' }}
          >
            <h2 className="text-sm font-semibold text-jarvis-text mb-4">Webhook Secret</h2>
            <div className="space-y-3">
              <div className="relative">
                <input
                  type={showSecret ? 'text' : 'password'}
                  value={webhookSecret}
                  onChange={(e) => setWebhookSecret(e.target.value)}
                  className="jarvis-input pr-10 font-mono text-xs"
                />
                <button
                  onClick={() => setShowSecret(!showSecret)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-jarvis-muted hover:text-jarvis-text"
                >
                  {showSecret ? <EyeOff size={13} /> : <Eye size={13} />}
                </button>
              </div>
              <button
                onClick={handleRegenerateSecret}
                disabled={isRegenerating}
                className="w-full flex items-center justify-center gap-2 py-2 rounded-lg text-xs font-semibold transition-all"
                style={{
                  backgroundColor: 'rgba(255,204,0,0.08)',
                  border: '1px solid rgba(255,204,0,0.2)',
                  color: '#ffcc00',
                }}
              >
                {isRegenerating ? <Loader2 size={11} className="animate-spin" /> : <RefreshCw size={11} />}
                Regenerate Secret
              </button>
            </div>
          </div>

          {/* Alert JSON Format */}
          <div
            className="rounded-xl p-5"
            style={{ backgroundColor: '#12121a', border: '1px solid #1e1e2e' }}
          >
            <h2 className="text-sm font-semibold text-jarvis-text mb-3">Alert JSON Format</h2>
            <pre
              className="text-[11px] font-mono text-jarvis-accent leading-relaxed p-3 rounded-lg overflow-auto"
              style={{ backgroundColor: '#0a0a14', border: '1px solid rgba(30,30,46,0.8)' }}
            >{`{
  "action": "BUY",
  "symbol": "XAUUSD",
  "price": {{close}},
  "sl": {{close}} - 15,
  "tp": {{close}} + 30,
  "strategy": "MyStrategy",
  "secret": "${webhookSecret.slice(0, 8)}..."
}`}</pre>
          </div>
        </div>

        {/* Signals + Pine Script */}
        <div className="xl:col-span-3 space-y-4">
          {/* Tabs */}
          <div
            className="flex gap-1 p-1 rounded-xl"
            style={{ backgroundColor: 'rgba(18,18,26,0.8)', border: '1px solid rgba(30,30,46,0.8)' }}
          >
            {[
              { id: 'signals', label: 'Signal History', icon: <Activity size={12} /> },
              { id: 'pinescript', label: 'Pine Script Template', icon: <Code size={12} /> },
            ].map(({ id, label, icon }) => (
              <button
                key={id}
                onClick={() => setActiveTab(id as 'signals' | 'pinescript')}
                className="flex items-center gap-2 flex-1 justify-center py-2 rounded-lg text-xs font-semibold transition-all"
                style={activeTab === id ? {
                  backgroundColor: 'rgba(0,212,255,0.1)',
                  border: '1px solid rgba(0,212,255,0.2)',
                  color: '#00d4ff',
                } : {
                  color: '#64748b',
                  border: '1px solid transparent',
                }}
              >
                {icon}
                {label}
              </button>
            ))}
          </div>

          {activeTab === 'signals' && (
            <>
              {/* Signal Chart */}
              <div
                className="rounded-xl p-5"
                style={{ backgroundColor: '#12121a', border: '1px solid #1e1e2e' }}
              >
                <h3 className="text-sm font-semibold text-jarvis-text mb-4">Signal Volume (20d)</h3>
                <ResponsiveContainer width="100%" height={120}>
                  <AreaChart data={signalChartData}>
                    <defs>
                      <linearGradient id="sigGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.3} />
                        <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(30,30,46,0.8)" />
                    <XAxis dataKey="day" stroke="#64748b" tick={{ fontSize: 9 }} axisLine={false} tickLine={false} />
                    <YAxis stroke="#64748b" tick={{ fontSize: 9 }} axisLine={false} tickLine={false} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#1a1a2e',
                        border: '1px solid rgba(139,92,246,0.3)',
                        borderRadius: '0.5rem',
                        fontSize: '0.7rem',
                        fontFamily: 'JetBrains Mono',
                      }}
                    />
                    <Area type="monotone" dataKey="signals" stroke="#8b5cf6" strokeWidth={2} fill="url(#sigGrad)" dot={false} name="Signals" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>

              {/* Signal Table */}
              <div
                className="rounded-xl overflow-hidden"
                style={{ backgroundColor: '#12121a', border: '1px solid #1e1e2e' }}
              >
                <div
                  className="px-5 py-4 border-b"
                  style={{ borderColor: '#1e1e2e' }}
                >
                  <h3 className="text-sm font-semibold text-jarvis-text">Recent Signals</h3>
                </div>
                <div className="overflow-x-auto">
                  <table className="jarvis-table">
                    <thead>
                      <tr>
                        <th>Symbol</th>
                        <th>Action</th>
                        <th>Price</th>
                        <th>SL</th>
                        <th>TP</th>
                        <th>Strategy</th>
                        <th>Time</th>
                        <th>Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {tradingViewSignals.map((signal) => (
                        <tr key={signal.id}>
                          <td className="font-bold text-jarvis-text">{signal.symbol}</td>
                          <td>
                            <span
                              className="inline-flex items-center gap-0.5 px-2 py-0.5 rounded text-[10px] font-bold"
                              style={{
                                backgroundColor: signal.action === 'BUY' ? 'rgba(0,255,136,0.1)' : 'rgba(255,51,102,0.1)',
                                color: signal.action === 'BUY' ? '#00ff88' : '#ff3366',
                              }}
                            >
                              {signal.action === 'BUY' ? <ArrowUpRight size={10} /> : <ArrowDownRight size={10} />}
                              {signal.action}
                            </span>
                          </td>
                          <td className="font-mono">{signal.price.toFixed(5)}</td>
                          <td className="font-mono text-jarvis-red">{signal.stopLoss.toFixed(5)}</td>
                          <td className="font-mono text-jarvis-green">{signal.takeProfit.toFixed(5)}</td>
                          <td className="text-jarvis-muted text-[11px]">{signal.strategy}</td>
                          <td className="text-jarvis-muted text-[11px]">
                            {format(parseISO(signal.timestamp), 'HH:mm')}
                          </td>
                          <td>
                            <span
                              className="text-[10px] px-2 py-0.5 rounded font-semibold"
                              style={signal.processed ? {
                                backgroundColor: 'rgba(0,255,136,0.1)',
                                color: '#00ff88',
                              } : {
                                backgroundColor: 'rgba(255,204,0,0.1)',
                                color: '#ffcc00',
                              }}
                            >
                              {signal.processed ? 'Done' : 'Pending'}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </>
          )}

          {activeTab === 'pinescript' && (
            <div
              className="rounded-xl overflow-hidden"
              style={{ backgroundColor: '#12121a', border: '1px solid #1e1e2e' }}
            >
              <div
                className="flex items-center justify-between px-5 py-4 border-b"
                style={{ borderColor: '#1e1e2e', backgroundColor: '#0d0d14' }}
              >
                <div className="flex items-center gap-2">
                  <Code size={14} style={{ color: '#8b5cf6' }} />
                  <span className="text-sm font-semibold text-jarvis-text">
                    JARVIS Webhook Strategy
                  </span>
                  <span
                    className="text-[10px] px-2 py-0.5 rounded font-semibold"
                    style={{ backgroundColor: 'rgba(139,92,246,0.15)', color: '#8b5cf6', border: '1px solid rgba(139,92,246,0.2)' }}
                  >
                    Pine Script v5
                  </span>
                </div>
                <button
                  onClick={handleCopyScript}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all"
                  style={{
                    backgroundColor: 'rgba(139,92,246,0.1)',
                    border: '1px solid rgba(139,92,246,0.2)',
                    color: '#8b5cf6',
                  }}
                >
                  {copiedScript ? <Check size={11} /> : <Copy size={11} />}
                  {copiedScript ? 'Copied!' : 'Copy Script'}
                </button>
              </div>
              <div className="overflow-auto" style={{ maxHeight: '500px' }}>
                <pre
                  className="text-[11px] font-mono p-5 leading-relaxed"
                  style={{ color: '#e2e8f0', backgroundColor: '#0a0a14' }}
                >
                  <code>{PINE_SCRIPT_TEMPLATE}</code>
                </pre>
              </div>
              <div
                className="px-5 py-4 border-t"
                style={{ borderColor: '#1e1e2e' }}
              >
                <div className="flex items-start gap-2">
                  <Zap size={12} style={{ color: '#ffcc00', marginTop: '2px', flexShrink: 0 }} />
                  <p className="text-[11px] text-jarvis-muted leading-relaxed">
                    Copy this Pine Script into TradingView. Update the webhook URL, then create alerts on your signals and check &ldquo;Webhook URL&rdquo; in the alert settings. JARVIS will automatically process and execute trades.
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
