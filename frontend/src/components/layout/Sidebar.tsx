'use client'

import { useJarvisStore } from '@/store/useJarvisStore'
import {
  LayoutDashboard,
  MessageSquare,
  TrendingUp,
  Layers,
  BarChart2,
  Code,
  Shield,
  Activity,
  Send,
  Settings,
  Zap,
  Wifi,
  WifiOff,
} from 'lucide-react'
import clsx from 'clsx'

interface SidebarProps {
  activeSection: string
  onNavigate: (section: string) => void
}

const navItems = [
  { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { id: 'chat', label: 'AI Chat', icon: MessageSquare },
  { id: 'trading', label: 'Trading', icon: TrendingUp },
  { id: 'strategies', label: 'Strategies', icon: Layers },
  { id: 'backtesting', label: 'Backtesting', icon: BarChart2 },
  { id: 'mql5', label: 'MQL5 Gen', icon: Code },
  { id: 'risk', label: 'Risk Manager', icon: Shield },
  { id: 'tradingview', label: 'TradingView', icon: Activity },
  { id: 'telegram', label: 'Telegram', icon: Send },
]

interface StatusDotProps {
  connected: boolean
  label: string
}

function StatusDot({ connected, label }: StatusDotProps) {
  return (
    <div className="flex items-center gap-1.5">
      <div className="relative">
        <div
          className={clsx('w-1.5 h-1.5 rounded-full', {
            'bg-jarvis-green': connected,
            'bg-jarvis-red': !connected,
          })}
        />
        {connected && (
          <div className="absolute inset-0 rounded-full bg-jarvis-green opacity-40 animate-ping" />
        )}
      </div>
      <span className={clsx('text-[10px] font-mono', {
        'text-jarvis-green': connected,
        'text-jarvis-red': !connected,
      })}>
        {label}
      </span>
    </div>
  )
}

export default function Sidebar({ activeSection, onNavigate }: SidebarProps) {
  const { connectionStatus } = useJarvisStore()

  return (
    <aside
      className="flex flex-col w-56 h-full border-r flex-shrink-0"
      style={{
        backgroundColor: '#0d0d14',
        borderColor: '#1e1e2e',
      }}
    >
      {/* Logo */}
      <div
        className="flex items-center gap-3 px-4 py-5 border-b"
        style={{ borderColor: '#1e1e2e' }}
      >
        <div
          className="relative flex items-center justify-center w-9 h-9 rounded-lg flex-shrink-0"
          style={{
            background: 'linear-gradient(135deg, rgba(0,212,255,0.2), rgba(139,92,246,0.2))',
            border: '1px solid rgba(0,212,255,0.3)',
            boxShadow: '0 0 12px rgba(0,212,255,0.2)',
          }}
        >
          <Zap size={18} style={{ color: '#00d4ff' }} />
        </div>
        <div>
          <div
            className="text-sm font-bold tracking-widest"
            style={{
              background: 'linear-gradient(135deg, #00d4ff, #8b5cf6)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
            }}
          >
            JARVIS
          </div>
          <div className="text-[10px] text-jarvis-muted tracking-wider">
            AI TRADING OS
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-3 overflow-y-auto">
        {navItems.map((item) => {
          const Icon = item.icon
          const isActive = activeSection === item.id

          return (
            <button
              key={item.id}
              onClick={() => onNavigate(item.id)}
              className={clsx(
                'w-full flex items-center gap-3 px-4 py-2.5 text-left transition-all duration-150 group relative',
                {
                  'text-jarvis-accent': isActive,
                  'text-jarvis-muted hover:text-jarvis-text': !isActive,
                }
              )}
              style={isActive ? {
                background: 'linear-gradient(90deg, rgba(0,212,255,0.08), transparent)',
              } : undefined}
            >
              {isActive && (
                <div
                  className="absolute left-0 top-0 bottom-0 w-0.5"
                  style={{
                    background: 'linear-gradient(180deg, #00d4ff, #8b5cf6)',
                    boxShadow: '0 0 6px rgba(0,212,255,0.5)',
                  }}
                />
              )}
              <Icon
                size={15}
                className={clsx('flex-shrink-0 transition-all', {
                  'drop-shadow-[0_0_4px_rgba(0,212,255,0.6)]': isActive,
                })}
              />
              <span className="text-xs font-medium tracking-wide">
                {item.label}
              </span>
              {item.id === 'chat' && (
                <span
                  className="ml-auto text-[9px] px-1.5 py-0.5 rounded font-bold"
                  style={{
                    background: 'rgba(139,92,246,0.2)',
                    color: '#8b5cf6',
                    border: '1px solid rgba(139,92,246,0.3)',
                  }}
                >
                  AI
                </span>
              )}
            </button>
          )
        })}

        {/* Settings divider */}
        <div className="mx-4 my-2 border-t" style={{ borderColor: '#1e1e2e' }} />
        <button
          onClick={() => onNavigate('settings')}
          className={clsx(
            'w-full flex items-center gap-3 px-4 py-2.5 text-left transition-all duration-150',
            activeSection === 'settings'
              ? 'text-jarvis-accent'
              : 'text-jarvis-muted hover:text-jarvis-text'
          )}
        >
          <Settings size={15} className="flex-shrink-0" />
          <span className="text-xs font-medium tracking-wide">Settings</span>
        </button>
      </nav>

      {/* Connection Status */}
      <div
        className="px-4 py-4 border-t"
        style={{ borderColor: '#1e1e2e' }}
      >
        <div className="text-[10px] text-jarvis-muted font-medium tracking-wider mb-2.5 uppercase">
          Connections
        </div>
        <div className="flex flex-col gap-1.5">
          <StatusDot connected={connectionStatus.mt5} label="MT5" />
          <StatusDot connected={connectionStatus.ai} label="AI Engine" />
          <StatusDot connected={connectionStatus.telegram} label="Telegram" />
          <StatusDot connected={connectionStatus.websocket} label="WebSocket" />
        </div>
      </div>

      {/* Version */}
      <div
        className="px-4 pb-3 text-[10px] text-jarvis-muted"
        style={{ borderColor: '#1e1e2e' }}
      >
        v1.0.0 • JARVIS OS
      </div>
    </aside>
  )
}
