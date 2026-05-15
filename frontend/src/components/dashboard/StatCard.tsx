'use client'

import { TrendingUp, TrendingDown, Minus } from 'lucide-react'
import clsx from 'clsx'
import { ReactNode } from 'react'

interface StatCardProps {
  title: string
  value: string
  change?: number
  changeLabel?: string
  icon: ReactNode
  variant?: 'default' | 'positive' | 'negative' | 'warning' | 'accent'
  subtitle?: string
  animated?: boolean
}

export default function StatCard({
  title,
  value,
  change,
  changeLabel,
  icon,
  variant = 'default',
  subtitle,
  animated = false,
}: StatCardProps) {
  const isPositive = change !== undefined && change > 0
  const isNegative = change !== undefined && change < 0

  const borderColor = {
    default: 'rgba(30,30,46,0.8)',
    positive: 'rgba(0,255,136,0.2)',
    negative: 'rgba(255,51,102,0.2)',
    warning: 'rgba(255,204,0,0.2)',
    accent: 'rgba(0,212,255,0.2)',
  }[variant]

  const glowColor = {
    default: 'none',
    positive: '0 0 12px rgba(0,255,136,0.08)',
    negative: '0 0 12px rgba(255,51,102,0.08)',
    warning: '0 0 12px rgba(255,204,0,0.08)',
    accent: '0 0 12px rgba(0,212,255,0.08)',
  }[variant]

  const iconBgColor = {
    default: 'rgba(30,30,46,0.8)',
    positive: 'rgba(0,255,136,0.1)',
    negative: 'rgba(255,51,102,0.1)',
    warning: 'rgba(255,204,0,0.1)',
    accent: 'rgba(0,212,255,0.1)',
  }[variant]

  const iconColor = {
    default: '#64748b',
    positive: '#00ff88',
    negative: '#ff3366',
    warning: '#ffcc00',
    accent: '#00d4ff',
  }[variant]

  return (
    <div
      className="relative rounded-xl p-4 transition-all duration-200 hover:-translate-y-0.5 cursor-default"
      style={{
        backgroundColor: '#12121a',
        border: `1px solid ${borderColor}`,
        boxShadow: glowColor,
      }}
    >
      <div className="flex items-start justify-between mb-3">
        <div
          className="flex items-center justify-center w-9 h-9 rounded-lg"
          style={{ backgroundColor: iconBgColor, color: iconColor }}
        >
          {icon}
        </div>
        {change !== undefined && (
          <div
            className={clsx(
              'flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold',
              {
                'text-jarvis-green': isPositive,
                'text-jarvis-red': isNegative,
                'text-jarvis-muted': !isPositive && !isNegative,
              }
            )}
            style={{
              backgroundColor: isPositive
                ? 'rgba(0,255,136,0.1)'
                : isNegative
                ? 'rgba(255,51,102,0.1)'
                : 'rgba(100,116,139,0.1)',
            }}
          >
            {isPositive ? (
              <TrendingUp size={10} />
            ) : isNegative ? (
              <TrendingDown size={10} />
            ) : (
              <Minus size={10} />
            )}
            <span>
              {change > 0 ? '+' : ''}
              {change.toFixed(2)}%
            </span>
          </div>
        )}
      </div>

      <div className="space-y-0.5">
        <div className="text-xs text-jarvis-muted font-medium tracking-wider uppercase">
          {title}
        </div>
        <div
          className={clsx('text-xl font-bold font-mono', {
            'text-jarvis-text': variant === 'default',
            'text-jarvis-green': variant === 'positive',
            'text-jarvis-red': variant === 'negative',
            'text-jarvis-yellow': variant === 'warning',
            'text-jarvis-accent': variant === 'accent',
          })}
          style={animated ? {
            textShadow: variant === 'positive'
              ? '0 0 8px rgba(0,255,136,0.4)'
              : variant === 'accent'
              ? '0 0 8px rgba(0,212,255,0.4)'
              : undefined,
          } : undefined}
        >
          {value}
        </div>
        {(changeLabel || subtitle) && (
          <div className="text-[11px] text-jarvis-muted">
            {changeLabel || subtitle}
          </div>
        )}
      </div>
    </div>
  )
}
