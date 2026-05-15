'use client'

import { useState } from 'react'
import { useJarvisStore } from '@/store/useJarvisStore'
import { Strategy } from '@/types'
import {
  Layers,
  Plus,
  Play,
  Pause,
  BarChart2,
  Trash2,
  TrendingUp,
  Target,
  Award,
  Activity,
  ChevronRight,
  Zap,
} from 'lucide-react'
import clsx from 'clsx'
import toast from 'react-hot-toast'

const STATUS_COLORS = {
  ACTIVE: { bg: 'rgba(0,255,136,0.1)', border: 'rgba(0,255,136,0.2)', text: '#00ff88' },
  INACTIVE: { bg: 'rgba(100,116,139,0.1)', border: 'rgba(100,116,139,0.2)', text: '#64748b' },
  TESTING: { bg: 'rgba(255,204,0,0.1)', border: 'rgba(255,204,0,0.2)', text: '#ffcc00' },
}

const TYPE_COLORS: Record<string, string> = {
  ICT: '#00d4ff',
  Trend: '#8b5cf6',
  Breakout: '#ffcc00',
  News: '#ff3366',
  Scalping: '#00ff88',
}

interface StrategyCardProps {
  strategy: Strategy
  onToggle: (id: number, active: boolean) => void
  onDelete: (id: number) => void
  isSelected: boolean
  onSelect: (id: number) => void
}

function StrategyCard({ strategy, onToggle, onDelete, isSelected, onSelect }: StrategyCardProps) {
  const status = STATUS_COLORS[strategy.status]
  const typeColor = TYPE_COLORS[strategy.type] || '#64748b'

  return (
    <div
      className={clsx(
        'rounded-xl p-4 transition-all duration-150 cursor-pointer',
        isSelected && 'ring-1 ring-jarvis-accent'
      )}
      style={{
        backgroundColor: '#12121a',
        border: isSelected ? '1px solid rgba(0,212,255,0.3)' : '1px solid #1e1e2e',
        boxShadow: isSelected ? '0 0 12px rgba(0,212,255,0.08)' : 'none',
      }}
      onClick={() => onSelect(strategy.id)}
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2.5">
          <div
            className="w-8 h-8 rounded-lg flex items-center justify-center text-[11px] font-bold"
            style={{ backgroundColor: `${typeColor}15`, color: typeColor, border: `1px solid ${typeColor}30` }}
          >
            {strategy.type.slice(0, 3)}
          </div>
          <div>
            <div className="text-sm font-semibold text-jarvis-text">{strategy.name}</div>
            <div className="text-[11px] text-jarvis-muted">{strategy.type} Strategy</div>
          </div>
        </div>
        <span
          className="text-[10px] font-bold px-2 py-0.5 rounded-full"
          style={{ backgroundColor: status.bg, border: `1px solid ${status.border}`, color: status.text }}
        >
          {strategy.status}
        </span>
      </div>

      <p className="text-[11px] text-jarvis-muted mb-3 leading-relaxed line-clamp-2">
        {strategy.description}
      </p>

      {/* Metrics */}
      <div className="grid grid-cols-3 gap-2 mb-3">
        <div
          className="text-center py-2 rounded-lg"
          style={{ backgroundColor: 'rgba(30,30,46,0.4)' }}
        >
          <div className="text-sm font-bold" style={{ color: '#00ff88' }}>
            {strategy.winrate.toFixed(1)}%
          </div>
          <div className="text-[10px] text-jarvis-muted">Winrate</div>
        </div>
        <div
          className="text-center py-2 rounded-lg"
          style={{ backgroundColor: 'rgba(30,30,46,0.4)' }}
        >
          <div className="text-sm font-bold text-jarvis-accent">
            {strategy.profitFactor.toFixed(2)}
          </div>
          <div className="text-[10px] text-jarvis-muted">Profit F</div>
        </div>
        <div
          className="text-center py-2 rounded-lg"
          style={{ backgroundColor: 'rgba(30,30,46,0.4)' }}
        >
          <div className="text-sm font-bold text-jarvis-text">
            {strategy.totalTrades}
          </div>
          <div className="text-[10px] text-jarvis-muted">Trades</div>
        </div>
      </div>

      {/* Winrate Bar */}
      <div
        className="h-1 rounded-full overflow-hidden mb-3"
        style={{ backgroundColor: 'rgba(30,30,46,0.8)' }}
      >
        <div
          className="h-full rounded-full"
          style={{
            width: `${strategy.winrate}%`,
            background: `linear-gradient(90deg, ${typeColor}, ${typeColor}80)`,
          }}
        />
      </div>

      {/* Actions */}
      <div className="flex gap-2" onClick={(e) => e.stopPropagation()}>
        <button
          onClick={() => onToggle(strategy.id, strategy.status !== 'ACTIVE')}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-semibold transition-all flex-1 justify-center"
          style={strategy.status === 'ACTIVE' ? {
            backgroundColor: 'rgba(255,51,102,0.1)',
            border: '1px solid rgba(255,51,102,0.2)',
            color: '#ff3366',
          } : {
            backgroundColor: 'rgba(0,255,136,0.1)',
            border: '1px solid rgba(0,255,136,0.2)',
            color: '#00ff88',
          }}
        >
          {strategy.status === 'ACTIVE' ? <Pause size={11} /> : <Play size={11} />}
          {strategy.status === 'ACTIVE' ? 'Pause' : 'Activate'}
        </button>
        <button
          className="flex items-center justify-center w-8 h-8 rounded-lg transition-all"
          style={{
            backgroundColor: 'rgba(0,212,255,0.06)',
            border: '1px solid rgba(0,212,255,0.15)',
            color: '#00d4ff',
          }}
          title="View backtest"
        >
          <BarChart2 size={12} />
        </button>
        <button
          onClick={() => onDelete(strategy.id)}
          className="flex items-center justify-center w-8 h-8 rounded-lg transition-all"
          style={{
            backgroundColor: 'rgba(255,51,102,0.06)',
            border: '1px solid rgba(255,51,102,0.15)',
            color: '#ff3366',
          }}
          title="Delete strategy"
        >
          <Trash2 size={12} />
        </button>
      </div>
    </div>
  )
}

export default function StrategyManager() {
  const { strategies, updateStrategy, addStrategy } = useJarvisStore()
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [filterStatus, setFilterStatus] = useState<'ALL' | 'ACTIVE' | 'INACTIVE' | 'TESTING'>('ALL')

  const filtered = strategies.filter((s) => filterStatus === 'ALL' || s.status === filterStatus)
  const activeCount = strategies.filter((s) => s.status === 'ACTIVE').length
  const totalWinrate = strategies.length > 0
    ? strategies.reduce((sum, s) => sum + s.winrate, 0) / strategies.length
    : 0

  const handleToggle = (id: number, activate: boolean) => {
    updateStrategy(id, { status: activate ? 'ACTIVE' : 'INACTIVE' })
    const s = strategies.find((x) => x.id === id)
    toast.success(`${s?.name} ${activate ? 'activated' : 'paused'}`)
  }

  const handleDelete = (id: number) => {
    const s = strategies.find((x) => x.id === id)
    toast((t) => (
      <div className="flex flex-col gap-3">
        <div className="text-sm">Delete <strong>{s?.name}</strong>?</div>
        <div className="flex gap-2">
          <button
            className="px-3 py-1.5 rounded text-xs font-semibold"
            style={{ backgroundColor: 'rgba(255,51,102,0.2)', border: '1px solid rgba(255,51,102,0.4)', color: '#ff3366' }}
            onClick={() => {
              updateStrategy(id, { status: 'INACTIVE' })
              toast.dismiss(t.id)
              toast.success('Strategy deleted')
            }}
          >
            Delete
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
    ), { duration: 8000 })
  }

  return (
    <div className="p-6 space-y-6" style={{ backgroundColor: '#0a0a0f', minHeight: '100%' }}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-jarvis-text">Strategy Manager</h1>
          <p className="text-xs text-jarvis-muted mt-0.5">
            {activeCount} active • {strategies.length} total strategies
          </p>
        </div>
        <button
          className="flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-semibold transition-all"
          style={{
            background: 'linear-gradient(135deg, rgba(0,212,255,0.15), rgba(139,92,246,0.15))',
            border: '1px solid rgba(0,212,255,0.3)',
            color: '#00d4ff',
          }}
        >
          <Plus size={14} />
          New Strategy
        </button>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: 'Total Strategies', value: String(strategies.length), icon: <Layers size={14} />, color: '#00d4ff' },
          { label: 'Active', value: String(activeCount), icon: <Activity size={14} />, color: '#00ff88' },
          { label: 'Avg Winrate', value: `${totalWinrate.toFixed(1)}%`, icon: <Target size={14} />, color: '#8b5cf6' },
          {
            label: 'Best PF',
            value: strategies.length > 0
              ? String(Math.max(...strategies.map((s) => s.profitFactor)).toFixed(2))
              : '0',
            icon: <Award size={14} />,
            color: '#ffcc00',
          },
        ].map(({ label, value, icon, color }) => (
          <div
            key={label}
            className="rounded-xl p-4"
            style={{ backgroundColor: '#12121a', border: '1px solid rgba(30,30,46,0.8)' }}
          >
            <div className="flex items-center gap-2 mb-2">
              <div style={{ color }}>{icon}</div>
              <span className="text-[11px] text-jarvis-muted uppercase tracking-wider">{label}</span>
            </div>
            <div className="text-2xl font-bold font-mono" style={{ color }}>
              {value}
            </div>
          </div>
        ))}
      </div>

      {/* Filter */}
      <div className="flex gap-2">
        {(['ALL', 'ACTIVE', 'INACTIVE', 'TESTING'] as const).map((status) => (
          <button
            key={status}
            onClick={() => setFilterStatus(status)}
            className="px-3 py-1.5 rounded-lg text-xs font-semibold transition-all"
            style={filterStatus === status ? {
              backgroundColor: 'rgba(0,212,255,0.1)',
              border: '1px solid rgba(0,212,255,0.3)',
              color: '#00d4ff',
            } : {
              backgroundColor: 'rgba(30,30,46,0.4)',
              border: '1px solid rgba(30,30,46,0.8)',
              color: '#64748b',
            }}
          >
            {status}
            <span
              className="ml-1.5 text-[10px]"
              style={{ opacity: 0.7 }}
            >
              ({status === 'ALL' ? strategies.length : strategies.filter((s) => s.status === status).length})
            </span>
          </button>
        ))}
      </div>

      {/* Strategy Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-4">
        {filtered.map((strategy) => (
          <StrategyCard
            key={strategy.id}
            strategy={strategy}
            onToggle={handleToggle}
            onDelete={handleDelete}
            isSelected={selectedId === strategy.id}
            onSelect={setSelectedId}
          />
        ))}
        {filtered.length === 0 && (
          <div className="col-span-3 py-16 text-center">
            <Layers size={32} className="mx-auto text-jarvis-muted opacity-30 mb-3" />
            <div className="text-jarvis-muted text-sm">No strategies found</div>
          </div>
        )}
      </div>
    </div>
  )
}
