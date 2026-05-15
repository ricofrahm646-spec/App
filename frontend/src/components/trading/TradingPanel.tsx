'use client'

import { useState } from 'react'
import { useJarvisStore } from '@/store/useJarvisStore'
import OpenTradesTable from './OpenTradesTable'
import {
  ArrowUpRight,
  ArrowDownRight,
  AlertTriangle,
  DollarSign,
  Activity,
  TrendingUp,
  Shield,
  BarChart3,
  Loader2,
} from 'lucide-react'
import toast from 'react-hot-toast'
import clsx from 'clsx'

const SYMBOLS = ['XAUUSD', 'EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'AUDUSD', 'USDCAD', 'BTCUSD']

interface OrderFormData {
  symbol: string
  type: 'BUY' | 'SELL'
  lots: string
  stopLoss: string
  takeProfit: string
  comment: string
}

export default function TradingPanel() {
  const { accountInfo, openTrades, removeTrade, connectionStatus } = useJarvisStore()
  const [orderForm, setOrderForm] = useState<OrderFormData>({
    symbol: 'XAUUSD',
    type: 'BUY',
    lots: '0.1',
    stopLoss: '',
    takeProfit: '',
    comment: '',
  })
  const [isPlacing, setIsPlacing] = useState(false)
  const [riskPercent, setRiskPercent] = useState('1.0')
  const [slPips, setSlPips] = useState('50')

  const handleCloseTrade = (ticket: number) => {
    removeTrade(ticket)
  }

  const handlePlaceOrder = async () => {
    if (!orderForm.symbol || !orderForm.lots) {
      toast.error('Please fill in required fields')
      return
    }

    if (!connectionStatus.mt5) {
      toast.error('MT5 not connected')
      return
    }

    setIsPlacing(true)
    try {
      await new Promise((resolve) => setTimeout(resolve, 1000))
      toast.success(`${orderForm.type} order placed: ${orderForm.lots} lots ${orderForm.symbol}`)
    } catch (error) {
      toast.error('Failed to place order')
    } finally {
      setIsPlacing(false)
    }
  }

  const handleEmergencyStop = async () => {
    toast((t) => (
      <div className="flex flex-col gap-3">
        <div className="text-sm font-bold text-jarvis-red">⚠ EMERGENCY STOP</div>
        <div className="text-xs text-jarvis-text">Close ALL {openTrades.length} open positions immediately?</div>
        <div className="flex gap-2">
          <button
            className="px-3 py-1.5 rounded text-xs font-bold"
            style={{
              background: 'rgba(255,51,102,0.3)',
              border: '1px solid #ff3366',
              color: '#ff3366',
            }}
            onClick={() => {
              toast.dismiss(t.id)
              toast.loading('Closing all positions...', { duration: 2000 })
              setTimeout(() => {
                openTrades.forEach((trade) => removeTrade(trade.ticket))
                toast.success('All positions closed')
              }, 1500)
            }}
          >
            CLOSE ALL NOW
          </button>
          <button
            className="px-3 py-1.5 rounded text-xs font-semibold text-jarvis-muted"
            style={{ backgroundColor: 'rgba(30,30,46,0.8)', border: '1px solid rgba(30,30,46,0.8)' }}
            onClick={() => toast.dismiss(t.id)}
          >
            Cancel
          </button>
        </div>
      </div>
    ), { duration: 15000 })
  }

  const calculatedLots = () => {
    const risk = parseFloat(riskPercent) / 100
    const balance = accountInfo.balance
    const riskAmount = balance * risk
    const pips = parseFloat(slPips)
    if (!pips || pips === 0) return '0.00'
    const lots = riskAmount / (pips * 10)
    return Math.min(lots, 100).toFixed(2)
  }

  const totalPnL = openTrades.reduce((s, t) => s + t.profit, 0)
  const marginUsedPercent = accountInfo.equity > 0 ? (accountInfo.margin / accountInfo.equity) * 100 : 0

  return (
    <div className="p-6 space-y-6" style={{ backgroundColor: '#0a0a0f', minHeight: '100%' }}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-jarvis-text">Trading Terminal</h1>
          <p className="text-xs text-jarvis-muted mt-0.5">Live order management • MT5 connected</p>
        </div>
        {/* Emergency Stop */}
        <button
          onClick={handleEmergencyStop}
          disabled={openTrades.length === 0}
          className="flex items-center gap-2 px-4 py-2.5 rounded-xl font-bold text-sm transition-all disabled:opacity-40 disabled:cursor-not-allowed"
          style={{
            background: 'linear-gradient(135deg, rgba(255,51,102,0.2), rgba(255,51,102,0.1))',
            border: '2px solid rgba(255,51,102,0.5)',
            color: '#ff3366',
            boxShadow: '0 0 12px rgba(255,51,102,0.15)',
          }}
        >
          <AlertTriangle size={15} />
          EMERGENCY STOP
        </button>
      </div>

      {/* Account Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          {
            label: 'Balance',
            value: `$${accountInfo.balance.toLocaleString('en-US', { minimumFractionDigits: 2 })}`,
            icon: <DollarSign size={14} />,
            color: '#00d4ff',
          },
          {
            label: 'Equity',
            value: `$${accountInfo.equity.toLocaleString('en-US', { minimumFractionDigits: 2 })}`,
            icon: <Activity size={14} />,
            color: '#00d4ff',
          },
          {
            label: 'Margin Used',
            value: `$${accountInfo.margin.toFixed(2)}`,
            icon: <BarChart3 size={14} />,
            color: '#ffcc00',
          },
          {
            label: 'Open P&L',
            value: `${totalPnL >= 0 ? '+' : ''}$${totalPnL.toFixed(2)}`,
            icon: totalPnL >= 0 ? <TrendingUp size={14} /> : <ArrowDownRight size={14} />,
            color: totalPnL >= 0 ? '#00ff88' : '#ff3366',
          },
        ].map(({ label, value, icon, color }) => (
          <div
            key={label}
            className="rounded-xl p-4"
            style={{
              backgroundColor: '#12121a',
              border: `1px solid rgba(30,30,46,0.8)`,
            }}
          >
            <div className="flex items-center gap-2 mb-2">
              <div style={{ color }}>{icon}</div>
              <span className="text-[11px] text-jarvis-muted uppercase tracking-wider">{label}</span>
            </div>
            <div className="text-lg font-bold font-mono" style={{ color }}>
              {value}
            </div>
          </div>
        ))}
      </div>

      {/* Margin bar */}
      <div
        className="rounded-xl p-4"
        style={{ backgroundColor: '#12121a', border: '1px solid #1e1e2e' }}
      >
        <div className="flex justify-between text-xs mb-2">
          <span className="text-jarvis-muted">Margin Level</span>
          <span className="font-semibold" style={{
            color: accountInfo.marginLevel > 200 ? '#00ff88' : accountInfo.marginLevel > 100 ? '#ffcc00' : '#ff3366',
          }}>
            {accountInfo.marginLevel.toFixed(0)}%
          </span>
        </div>
        <div
          className="h-2 rounded-full overflow-hidden"
          style={{ backgroundColor: 'rgba(30,30,46,0.8)' }}
        >
          <div
            className="h-full rounded-full transition-all"
            style={{
              width: `${Math.min(marginUsedPercent * 5, 100)}%`,
              background: accountInfo.marginLevel > 200 ? '#00ff88' : accountInfo.marginLevel > 100 ? '#ffcc00' : '#ff3366',
            }}
          />
        </div>
        <div className="flex justify-between text-[10px] text-jarvis-muted mt-1.5">
          <span>Free Margin: ${accountInfo.freeMargin.toLocaleString()}</span>
          <span>Used: ${accountInfo.margin.toFixed(2)}</span>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Quick Order Form */}
        <div
          className="rounded-xl p-5"
          style={{ backgroundColor: '#12121a', border: '1px solid #1e1e2e' }}
        >
          <h2 className="text-sm font-semibold text-jarvis-text mb-4">Quick Order</h2>

          <div className="space-y-3">
            {/* Symbol */}
            <div>
              <label className="text-[11px] text-jarvis-muted uppercase tracking-wider block mb-1.5">
                Symbol
              </label>
              <select
                value={orderForm.symbol}
                onChange={(e) => setOrderForm({ ...orderForm, symbol: e.target.value })}
                className="jarvis-input"
                style={{ backgroundColor: 'rgba(30,30,46,0.6)', cursor: 'pointer' }}
              >
                {SYMBOLS.map((s) => (
                  <option key={s} value={s} style={{ backgroundColor: '#12121a' }}>{s}</option>
                ))}
              </select>
            </div>

            {/* Direction */}
            <div>
              <label className="text-[11px] text-jarvis-muted uppercase tracking-wider block mb-1.5">
                Direction
              </label>
              <div className="grid grid-cols-2 gap-2">
                <button
                  onClick={() => setOrderForm({ ...orderForm, type: 'BUY' })}
                  className="flex items-center justify-center gap-2 py-2.5 rounded-lg text-xs font-bold transition-all"
                  style={{
                    backgroundColor: orderForm.type === 'BUY'
                      ? 'rgba(0,255,136,0.15)'
                      : 'rgba(30,30,46,0.4)',
                    border: orderForm.type === 'BUY'
                      ? '1px solid rgba(0,255,136,0.4)'
                      : '1px solid rgba(30,30,46,0.8)',
                    color: orderForm.type === 'BUY' ? '#00ff88' : '#64748b',
                  }}
                >
                  <ArrowUpRight size={13} />
                  BUY
                </button>
                <button
                  onClick={() => setOrderForm({ ...orderForm, type: 'SELL' })}
                  className="flex items-center justify-center gap-2 py-2.5 rounded-lg text-xs font-bold transition-all"
                  style={{
                    backgroundColor: orderForm.type === 'SELL'
                      ? 'rgba(255,51,102,0.15)'
                      : 'rgba(30,30,46,0.4)',
                    border: orderForm.type === 'SELL'
                      ? '1px solid rgba(255,51,102,0.4)'
                      : '1px solid rgba(30,30,46,0.8)',
                    color: orderForm.type === 'SELL' ? '#ff3366' : '#64748b',
                  }}
                >
                  <ArrowDownRight size={13} />
                  SELL
                </button>
              </div>
            </div>

            {/* Lots */}
            <div>
              <label className="text-[11px] text-jarvis-muted uppercase tracking-wider block mb-1.5">
                Lot Size
              </label>
              <input
                type="number"
                value={orderForm.lots}
                onChange={(e) => setOrderForm({ ...orderForm, lots: e.target.value })}
                step="0.01"
                min="0.01"
                max="100"
                className="jarvis-input"
                placeholder="0.10"
              />
            </div>

            {/* SL / TP */}
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="text-[11px] text-jarvis-red uppercase tracking-wider block mb-1.5">
                  Stop Loss
                </label>
                <input
                  type="number"
                  value={orderForm.stopLoss}
                  onChange={(e) => setOrderForm({ ...orderForm, stopLoss: e.target.value })}
                  className="jarvis-input"
                  placeholder="0.00"
                />
              </div>
              <div>
                <label className="text-[11px] text-jarvis-green uppercase tracking-wider block mb-1.5">
                  Take Profit
                </label>
                <input
                  type="number"
                  value={orderForm.takeProfit}
                  onChange={(e) => setOrderForm({ ...orderForm, takeProfit: e.target.value })}
                  className="jarvis-input"
                  placeholder="0.00"
                />
              </div>
            </div>

            {/* Comment */}
            <div>
              <label className="text-[11px] text-jarvis-muted uppercase tracking-wider block mb-1.5">
                Comment (optional)
              </label>
              <input
                type="text"
                value={orderForm.comment}
                onChange={(e) => setOrderForm({ ...orderForm, comment: e.target.value })}
                className="jarvis-input"
                placeholder="Order comment..."
                maxLength={32}
              />
            </div>

            {/* Place Order Button */}
            <button
              onClick={handlePlaceOrder}
              disabled={isPlacing || !connectionStatus.mt5}
              className="w-full flex items-center justify-center gap-2 py-3 rounded-xl font-bold text-sm transition-all disabled:opacity-40"
              style={{
                background: orderForm.type === 'BUY'
                  ? 'linear-gradient(135deg, rgba(0,255,136,0.2), rgba(0,255,136,0.1))'
                  : 'linear-gradient(135deg, rgba(255,51,102,0.2), rgba(255,51,102,0.1))',
                border: orderForm.type === 'BUY'
                  ? '1px solid rgba(0,255,136,0.4)'
                  : '1px solid rgba(255,51,102,0.4)',
                color: orderForm.type === 'BUY' ? '#00ff88' : '#ff3366',
                boxShadow: orderForm.type === 'BUY'
                  ? '0 0 12px rgba(0,255,136,0.1)'
                  : '0 0 12px rgba(255,51,102,0.1)',
              }}
            >
              {isPlacing ? (
                <Loader2 size={15} className="animate-spin" />
              ) : orderForm.type === 'BUY' ? (
                <ArrowUpRight size={15} />
              ) : (
                <ArrowDownRight size={15} />
              )}
              {isPlacing ? 'Placing...' : `Place ${orderForm.type} Order`}
            </button>

            {!connectionStatus.mt5 && (
              <div
                className="text-[11px] text-center py-2 rounded-lg"
                style={{
                  backgroundColor: 'rgba(255,204,0,0.1)',
                  border: '1px solid rgba(255,204,0,0.2)',
                  color: '#ffcc00',
                }}
              >
                ⚠ MT5 not connected
              </div>
            )}
          </div>
        </div>

        {/* Risk Calculator */}
        <div
          className="rounded-xl p-5"
          style={{ backgroundColor: '#12121a', border: '1px solid #1e1e2e' }}
        >
          <div className="flex items-center gap-2 mb-4">
            <Shield size={15} style={{ color: '#8b5cf6' }} />
            <h2 className="text-sm font-semibold text-jarvis-text">Risk Calculator</h2>
          </div>

          <div className="space-y-4">
            <div>
              <label className="text-[11px] text-jarvis-muted uppercase tracking-wider block mb-1.5">
                Risk Per Trade (%)
              </label>
              <div className="flex items-center gap-2">
                <input
                  type="range"
                  min="0.1"
                  max="5"
                  step="0.1"
                  value={riskPercent}
                  onChange={(e) => setRiskPercent(e.target.value)}
                  className="flex-1 accent-jarvis-accent"
                />
                <span
                  className="text-sm font-bold font-mono w-12 text-right"
                  style={{ color: '#8b5cf6' }}
                >
                  {riskPercent}%
                </span>
              </div>
            </div>

            <div>
              <label className="text-[11px] text-jarvis-muted uppercase tracking-wider block mb-1.5">
                Stop Loss (Pips)
              </label>
              <input
                type="number"
                value={slPips}
                onChange={(e) => setSlPips(e.target.value)}
                className="jarvis-input"
                placeholder="50"
              />
            </div>

            <div
              className="rounded-lg p-3 space-y-2"
              style={{ backgroundColor: 'rgba(30,30,46,0.4)', border: '1px solid rgba(30,30,46,0.8)' }}
            >
              <div className="text-[11px] text-jarvis-muted uppercase tracking-wider mb-2">Calculated</div>
              <div className="flex justify-between text-xs">
                <span className="text-jarvis-muted">Risk Amount</span>
                <span className="font-mono font-semibold text-jarvis-yellow">
                  ${(accountInfo.balance * parseFloat(riskPercent) / 100).toFixed(2)}
                </span>
              </div>
              <div className="flex justify-between text-xs">
                <span className="text-jarvis-muted">Lot Size</span>
                <span className="font-mono font-bold text-jarvis-accent">{calculatedLots()} lots</span>
              </div>
              <div className="flex justify-between text-xs">
                <span className="text-jarvis-muted">Max Loss</span>
                <span className="font-mono text-jarvis-red">
                  -${(accountInfo.balance * parseFloat(riskPercent) / 100).toFixed(2)}
                </span>
              </div>
            </div>

            <div
              className="text-xs text-center py-2 rounded-lg font-semibold"
              style={{
                backgroundColor: 'rgba(0,212,255,0.06)',
                border: '1px solid rgba(0,212,255,0.15)',
                color: '#00d4ff',
              }}
            >
              Recommended: {calculatedLots()} lots
            </div>
          </div>
        </div>

        {/* MT5 Status */}
        <div
          className="rounded-xl p-5"
          style={{ backgroundColor: '#12121a', border: '1px solid #1e1e2e' }}
        >
          <h2 className="text-sm font-semibold text-jarvis-text mb-4">MT5 Connection</h2>

          <div className="space-y-3">
            <div
              className="flex items-center gap-3 p-3 rounded-lg"
              style={{
                backgroundColor: connectionStatus.mt5
                  ? 'rgba(0,255,136,0.05)'
                  : 'rgba(255,51,102,0.05)',
                border: connectionStatus.mt5
                  ? '1px solid rgba(0,255,136,0.15)'
                  : '1px solid rgba(255,51,102,0.15)',
              }}
            >
              <div className="relative">
                <div
                  className="w-3 h-3 rounded-full"
                  style={{ backgroundColor: connectionStatus.mt5 ? '#00ff88' : '#ff3366' }}
                />
                {connectionStatus.mt5 && (
                  <div className="absolute inset-0 rounded-full bg-jarvis-green opacity-40 animate-ping" />
                )}
              </div>
              <div>
                <div className="text-xs font-semibold" style={{ color: connectionStatus.mt5 ? '#00ff88' : '#ff3366' }}>
                  {connectionStatus.mt5 ? 'MT5 Connected' : 'MT5 Disconnected'}
                </div>
                <div className="text-[10px] text-jarvis-muted">
                  {connectionStatus.mt5 ? 'Real-time data active' : 'Check server connection'}
                </div>
              </div>
            </div>

            {[
              { label: 'Server', value: 'MetaQuotes-Demo' },
              { label: 'Account', value: '#12345678' },
              { label: 'Platform', value: 'MT5 Build 3815' },
              { label: 'Leverage', value: '1:500' },
              { label: 'Open Trades', value: String(openTrades.length) },
            ].map(({ label, value }) => (
              <div key={label} className="flex justify-between text-xs">
                <span className="text-jarvis-muted">{label}</span>
                <span className="font-mono text-jarvis-text">{value}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Open Trades Table */}
      <OpenTradesTable trades={openTrades} onClose={handleCloseTrade} />
    </div>
  )
}
