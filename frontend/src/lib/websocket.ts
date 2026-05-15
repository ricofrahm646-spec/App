import { io, Socket } from 'socket.io-client'
import { useJarvisStore } from '@/store/useJarvisStore'
import { Trade, AccountInfo } from '@/types'

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000'

let socket: Socket | null = null
let reconnectTimer: ReturnType<typeof setTimeout> | null = null
let reconnectAttempts = 0
const MAX_RECONNECT_ATTEMPTS = 10
const RECONNECT_DELAY = 3000

export function connectWebSocket(): Socket {
  if (socket?.connected) return socket

  socket = io(WS_URL, {
    transports: ['websocket'],
    reconnection: true,
    reconnectionAttempts: MAX_RECONNECT_ATTEMPTS,
    reconnectionDelay: RECONNECT_DELAY,
    timeout: 10000,
  })

  socket.on('connect', () => {
    console.log('[WS] Connected:', socket?.id)
    reconnectAttempts = 0
    useJarvisStore.getState().setWebSocketStatus(true)
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
  })

  socket.on('disconnect', (reason) => {
    console.log('[WS] Disconnected:', reason)
    useJarvisStore.getState().setWebSocketStatus(false)
  })

  socket.on('connect_error', (error) => {
    console.error('[WS] Connection error:', error.message)
    reconnectAttempts++
    useJarvisStore.getState().setWebSocketStatus(false)
  })

  // Dashboard updates
  socket.on('dashboard_update', (data: {
    balance?: number
    equity?: number
    profit?: number
    winrate?: number
    openTrades?: number
    drawdown?: number
  }) => {
    const store = useJarvisStore.getState()
    store.updateDashboardData(data)
    if (data.balance !== undefined || data.equity !== undefined) {
      store.updateAccountInfo({
        balance: data.balance ?? store.accountInfo.balance,
        equity: data.equity ?? store.accountInfo.equity,
        profit: data.profit ?? store.accountInfo.profit,
      })
    }
  })

  // Trade events
  socket.on('trade_opened', (trade: Trade) => {
    useJarvisStore.getState().addTrade(trade)
  })

  socket.on('trade_closed', (data: { ticket: number; profit: number }) => {
    useJarvisStore.getState().removeTrade(data.ticket)
  })

  socket.on('trade_updated', (trade: Trade) => {
    useJarvisStore.getState().updateTrade(trade.ticket, trade)
  })

  // Account updates
  socket.on('account_update', (info: AccountInfo) => {
    useJarvisStore.getState().setAccountInfo(info)
  })

  // AI messages
  socket.on('ai_message', (data: { content: string; type: 'info' | 'warning' | 'error' }) => {
    console.log('[AI]', data.type, data.content)
  })

  // Alerts
  socket.on('alert', (data: {
    type: 'info' | 'warning' | 'error' | 'success'
    message: string
    symbol?: string
  }) => {
    console.log('[ALERT]', data)
  })

  // Connection status updates
  socket.on('mt5_status', (connected: boolean) => {
    useJarvisStore.getState().setMT5Status(connected)
  })

  socket.on('telegram_status', (connected: boolean) => {
    useJarvisStore.getState().setTelegramStatus(connected)
  })

  socket.on('ai_status', (status: 'idle' | 'thinking' | 'error') => {
    useJarvisStore.getState().setAiStatus(status)
  })

  // TradingView signals
  socket.on('tradingview_signal', (signal) => {
    useJarvisStore.getState().addTradingViewSignal(signal)
  })

  return socket
}

export function disconnectWebSocket(): void {
  if (reconnectTimer) {
    clearTimeout(reconnectTimer)
    reconnectTimer = null
  }
  if (socket) {
    socket.disconnect()
    socket = null
  }
}

export function getSocket(): Socket | null {
  return socket
}

export function isConnected(): boolean {
  return socket?.connected ?? false
}

export function emit(event: string, data?: unknown): void {
  if (socket?.connected) {
    socket.emit(event, data)
  } else {
    console.warn('[WS] Cannot emit, not connected:', event)
  }
}

export function subscribeToPrice(symbol: string): void {
  emit('subscribe_price', { symbol })
}

export function unsubscribeFromPrice(symbol: string): void {
  emit('unsubscribe_price', { symbol })
}
