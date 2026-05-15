'use client'

import { useState } from 'react'
import {
  Send,
  Eye,
  EyeOff,
  CheckCircle,
  XCircle,
  Loader2,
  MessageSquare,
  Bell,
  BarChart2,
  TrendingUp,
  AlertTriangle,
} from 'lucide-react'
import toast from 'react-hot-toast'
import { format } from 'date-fns'
import clsx from 'clsx'

interface Message {
  id: number
  text: string
  time: string
  type: 'trade' | 'alert' | 'report' | 'system'
}

const MOCK_MESSAGES: Message[] = [
  { id: 1, text: '✅ BUY XAUUSD 0.1 lots @ 2315.50 | SL: 2305 | TP: 2340', time: new Date(Date.now() - 3600000).toISOString(), type: 'trade' },
  { id: 2, text: '🚨 Alert: Daily P&L target reached (+$127.50)', time: new Date(Date.now() - 7200000).toISOString(), type: 'alert' },
  { id: 3, text: '📊 Daily Report: Balance $12,547 | Winrate 64.3% | DD 2.4%', time: new Date(Date.now() - 86400000).toISOString(), type: 'report' },
  { id: 4, text: '✅ SELL EURUSD 0.5 lots @ 1.0845 | SL: 1.0870 | TP: 1.0800', time: new Date(Date.now() - 9000000).toISOString(), type: 'trade' },
  { id: 5, text: '⚡ JARVIS system started. MT5 connected. AI engine ready.', time: new Date(Date.now() - 172800000).toISOString(), type: 'system' },
]

const MSG_ICONS = {
  trade: <TrendingUp size={12} />,
  alert: <AlertTriangle size={12} />,
  report: <BarChart2 size={12} />,
  system: <Bell size={12} />,
}

const MSG_COLORS = {
  trade: '#00ff88',
  alert: '#ffcc00',
  report: '#00d4ff',
  system: '#8b5cf6',
}

export default function TelegramConfig() {
  const [botToken, setBotToken] = useState('')
  const [chatId, setChatId] = useState('')
  const [showToken, setShowToken] = useState(false)
  const [isConnected, setIsConnected] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [isTesting, setIsTesting] = useState(false)

  const [sendTrades, setSendTrades] = useState(true)
  const [sendAlerts, setSendAlerts] = useState(true)
  const [sendReports, setSendReports] = useState(true)
  const [sendErrors, setSendErrors] = useState(true)

  const handleSave = async () => {
    if (!botToken || !chatId) {
      toast.error('Please enter bot token and chat ID')
      return
    }
    setIsSaving(true)
    await new Promise((r) => setTimeout(r, 1000))
    setIsSaving(false)
    setIsConnected(true)
    toast.success('Telegram configuration saved!')
  }

  const handleTest = async () => {
    if (!botToken || !chatId) {
      toast.error('Please save configuration first')
      return
    }
    setIsTesting(true)
    await new Promise((r) => setTimeout(r, 1500))
    setIsTesting(false)
    toast.success('Test message sent to Telegram!')
  }

  const handleDisconnect = () => {
    setIsConnected(false)
    setBotToken('')
    setChatId('')
    toast.success('Telegram disconnected')
  }

  return (
    <div className="p-6 space-y-6" style={{ backgroundColor: '#0a0a0f', minHeight: '100%' }}>
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-jarvis-text">Telegram Integration</h1>
        <p className="text-xs text-jarvis-muted mt-0.5">
          Configure bot notifications for trades, alerts, and reports
        </p>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        {/* Config Form */}
        <div
          className="rounded-xl p-5"
          style={{ backgroundColor: '#12121a', border: '1px solid #1e1e2e' }}
        >
          <div className="flex items-center justify-between mb-5">
            <div className="flex items-center gap-2">
              <Send size={15} style={{ color: '#00d4ff' }} />
              <h2 className="text-sm font-semibold text-jarvis-text">Bot Configuration</h2>
            </div>
            <div
              className="flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-semibold"
              style={isConnected ? {
                backgroundColor: 'rgba(0,255,136,0.1)',
                border: '1px solid rgba(0,255,136,0.2)',
                color: '#00ff88',
              } : {
                backgroundColor: 'rgba(100,116,139,0.1)',
                border: '1px solid rgba(100,116,139,0.2)',
                color: '#64748b',
              }}
            >
              <div className={clsx(
                'w-1.5 h-1.5 rounded-full',
                isConnected ? 'bg-jarvis-green animate-pulse' : 'bg-jarvis-muted'
              )} />
              {isConnected ? 'Connected' : 'Disconnected'}
            </div>
          </div>

          <div className="space-y-4">
            {/* Bot Token */}
            <div>
              <label className="text-[11px] text-jarvis-muted uppercase tracking-wider block mb-1.5">
                Bot Token
              </label>
              <div className="relative">
                <input
                  type={showToken ? 'text' : 'password'}
                  value={botToken}
                  onChange={(e) => setBotToken(e.target.value)}
                  className="jarvis-input pr-10"
                  placeholder="123456789:ABCdefGHIjklMNOpqrSTUvwxyz"
                />
                <button
                  onClick={() => setShowToken(!showToken)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-jarvis-muted hover:text-jarvis-text transition-colors"
                >
                  {showToken ? <EyeOff size={14} /> : <Eye size={14} />}
                </button>
              </div>
              <p className="text-[10px] text-jarvis-muted mt-1">
                Get from <span className="text-jarvis-accent">@BotFather</span> on Telegram
              </p>
            </div>

            {/* Chat ID */}
            <div>
              <label className="text-[11px] text-jarvis-muted uppercase tracking-wider block mb-1.5">
                Chat ID
              </label>
              <input
                type="text"
                value={chatId}
                onChange={(e) => setChatId(e.target.value)}
                className="jarvis-input"
                placeholder="-1001234567890"
              />
              <p className="text-[10px] text-jarvis-muted mt-1">
                Channel/group ID or personal chat ID
              </p>
            </div>

            {/* Notification Settings */}
            <div>
              <div className="text-[11px] text-jarvis-muted uppercase tracking-wider mb-3">
                Notification Types
              </div>
              <div className="space-y-2.5">
                {[
                  { label: 'Trade Notifications', desc: 'Open/close orders', value: sendTrades, set: setSendTrades, color: '#00ff88' },
                  { label: 'Alerts & Warnings', desc: 'Risk limits, drawdown', value: sendAlerts, set: setSendAlerts, color: '#ffcc00' },
                  { label: 'Daily Reports', desc: 'EOD performance summary', value: sendReports, set: setSendReports, color: '#00d4ff' },
                  { label: 'System Errors', desc: 'Connection issues', value: sendErrors, set: setSendErrors, color: '#ff3366' },
                ].map(({ label, desc, value, set, color }) => (
                  <div
                    key={label}
                    className="flex items-center justify-between p-3 rounded-lg"
                    style={{ backgroundColor: 'rgba(30,30,46,0.4)', border: '1px solid rgba(30,30,46,0.8)' }}
                  >
                    <div className="flex items-center gap-2.5">
                      <div
                        className="w-2 h-2 rounded-full"
                        style={{ backgroundColor: value ? color : '#64748b' }}
                      />
                      <div>
                        <div className="text-xs font-semibold text-jarvis-text">{label}</div>
                        <div className="text-[10px] text-jarvis-muted">{desc}</div>
                      </div>
                    </div>
                    <button
                      onClick={() => set(!value)}
                      className="relative inline-flex h-5 w-9 items-center rounded-full transition-colors"
                      style={{ backgroundColor: value ? color : 'rgba(30,30,46,0.8)' }}
                    >
                      <span
                        className="inline-block h-3.5 w-3.5 transform rounded-full bg-white transition-transform"
                        style={{ transform: value ? 'translateX(18px)' : 'translateX(2px)' }}
                      />
                    </button>
                  </div>
                ))}
              </div>
            </div>

            {/* Buttons */}
            <div className="flex gap-3">
              <button
                onClick={handleSave}
                disabled={isSaving}
                className="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-xl text-sm font-semibold transition-all"
                style={{
                  background: 'linear-gradient(135deg, rgba(0,212,255,0.2), rgba(0,212,255,0.1))',
                  border: '1px solid rgba(0,212,255,0.3)',
                  color: '#00d4ff',
                }}
              >
                {isSaving ? <Loader2 size={13} className="animate-spin" /> : <CheckCircle size={13} />}
                {isSaving ? 'Saving...' : 'Save Config'}
              </button>
              <button
                onClick={handleTest}
                disabled={isTesting}
                className="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-xl text-sm font-semibold transition-all"
                style={{
                  background: 'linear-gradient(135deg, rgba(0,255,136,0.15), rgba(0,255,136,0.08))',
                  border: '1px solid rgba(0,255,136,0.3)',
                  color: '#00ff88',
                }}
              >
                {isTesting ? <Loader2 size={13} className="animate-spin" /> : <Send size={13} />}
                {isTesting ? 'Sending...' : 'Test Send'}
              </button>
            </div>

            {isConnected && (
              <button
                onClick={handleDisconnect}
                className="w-full py-2 text-xs text-jarvis-red font-semibold rounded-lg transition-all"
                style={{ backgroundColor: 'rgba(255,51,102,0.06)', border: '1px solid rgba(255,51,102,0.15)' }}
              >
                Disconnect
              </button>
            )}
          </div>
        </div>

        {/* Recent Messages */}
        <div
          className="rounded-xl overflow-hidden"
          style={{ backgroundColor: '#12121a', border: '1px solid #1e1e2e' }}
        >
          <div
            className="flex items-center justify-between px-5 py-4 border-b"
            style={{ borderColor: '#1e1e2e' }}
          >
            <div className="flex items-center gap-2">
              <MessageSquare size={14} style={{ color: '#00d4ff' }} />
              <h2 className="text-sm font-semibold text-jarvis-text">Message History</h2>
            </div>
            <span className="text-[11px] text-jarvis-muted">{MOCK_MESSAGES.length} messages</span>
          </div>

          <div className="divide-y" style={{ borderColor: 'rgba(30,30,46,0.5)' }}>
            {MOCK_MESSAGES.map((msg) => (
              <div
                key={msg.id}
                className="flex gap-3 px-5 py-4 hover:bg-jarvis-border transition-colors"
                style={{ backgroundColor: 'transparent' }}
              >
                <div
                  className="flex-shrink-0 w-7 h-7 rounded-lg flex items-center justify-center mt-0.5"
                  style={{
                    backgroundColor: `${MSG_COLORS[msg.type]}15`,
                    color: MSG_COLORS[msg.type],
                  }}
                >
                  {MSG_ICONS[msg.type]}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-xs text-jarvis-text leading-relaxed">{msg.text}</p>
                  <p className="text-[10px] text-jarvis-muted mt-1">
                    {format(new Date(msg.time), 'MMM d, HH:mm')}
                  </p>
                </div>
              </div>
            ))}
          </div>

          {/* Setup Guide */}
          {!isConnected && (
            <div
              className="mx-5 mb-5 mt-3 p-4 rounded-xl"
              style={{ background: 'rgba(0,212,255,0.04)', border: '1px solid rgba(0,212,255,0.12)' }}
            >
              <div className="text-xs font-semibold text-jarvis-accent mb-2">Quick Setup Guide</div>
              <ol className="text-[11px] text-jarvis-muted space-y-1.5 list-none">
                {[
                  'Message @BotFather on Telegram',
                  'Use /newbot and follow instructions',
                  'Copy the bot token (keep it secret)',
                  'Add bot to your channel/group',
                  'Get chat ID from @userinfobot',
                  'Paste credentials above and save',
                ].map((step, i) => (
                  <li key={i} className="flex items-start gap-2">
                    <span
                      className="w-4 h-4 rounded-full text-[9px] font-bold flex items-center justify-center flex-shrink-0 mt-0.5"
                      style={{ backgroundColor: 'rgba(0,212,255,0.15)', color: '#00d4ff' }}
                    >
                      {i + 1}
                    </span>
                    {step}
                  </li>
                ))}
              </ol>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
