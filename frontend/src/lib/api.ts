import axios, { AxiosInstance, AxiosResponse } from 'axios'
import {
  AccountInfo,
  Trade,
  Strategy,
  BacktestResult,
  BacktestRequest,
  OrderRequest,
  RiskMetrics,
  TradingViewSignal,
  DashboardData,
  MQL5Config,
  TelegramConfig,
} from '@/types'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

apiClient.interceptors.request.use(
  (config) => {
    const token = typeof window !== 'undefined' ? localStorage.getItem('jarvis_token') : null
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

apiClient.interceptors.response.use(
  (response: AxiosResponse) => response,
  (error) => {
    if (error.response?.status === 401) {
      if (typeof window !== 'undefined') {
        localStorage.removeItem('jarvis_token')
      }
    }
    return Promise.reject(error)
  }
)

// Dashboard
export async function getDashboardData(): Promise<DashboardData> {
  const { data } = await apiClient.get('/api/dashboard')
  return data
}

// Account
export async function getAccountInfo(): Promise<AccountInfo> {
  const { data } = await apiClient.get('/api/mt5/account')
  return data
}

// Trades
export async function getOpenTrades(): Promise<Trade[]> {
  const { data } = await apiClient.get('/api/mt5/trades')
  return data
}

export async function placeOrder(order: OrderRequest): Promise<Trade> {
  const { data } = await apiClient.post('/api/mt5/order', order)
  return data
}

export async function closeOrder(ticket: number): Promise<{ success: boolean; message: string }> {
  const { data } = await apiClient.delete(`/api/mt5/trade/${ticket}`)
  return data
}

export async function closeAllOrders(): Promise<{ success: boolean; closed: number }> {
  const { data } = await apiClient.delete('/api/mt5/trades/all')
  return data
}

// Strategies
export async function getStrategies(): Promise<Strategy[]> {
  const { data } = await apiClient.get('/api/strategies')
  return data
}

export async function createStrategy(strategy: Partial<Strategy>): Promise<Strategy> {
  const { data } = await apiClient.post('/api/strategies', strategy)
  return data
}

export async function updateStrategy(id: number, updates: Partial<Strategy>): Promise<Strategy> {
  const { data } = await apiClient.put(`/api/strategies/${id}`, updates)
  return data
}

export async function deleteStrategy(id: number): Promise<{ success: boolean }> {
  const { data } = await apiClient.delete(`/api/strategies/${id}`)
  return data
}

export async function toggleStrategy(id: number, active: boolean): Promise<Strategy> {
  const { data } = await apiClient.post(`/api/strategies/${id}/toggle`, { active })
  return data
}

// Backtesting
export async function runBacktest(request: BacktestRequest): Promise<BacktestResult> {
  const { data } = await apiClient.post('/api/backtest/run', request)
  return data
}

export async function getBacktestHistory(): Promise<BacktestResult[]> {
  const { data } = await apiClient.get('/api/backtest/history')
  return data
}

// AI Chat
export async function sendChatMessage(
  message: string,
  history: { role: string; content: string }[]
): Promise<{ response: string; files?: { path: string; type: string; name: string }[] }> {
  const { data } = await apiClient.post('/api/ai/chat', { message, history })
  return data
}

export async function streamChatMessage(
  message: string,
  history: { role: string; content: string }[],
  onChunk: (chunk: string) => void,
  onComplete: (files?: { path: string; type: string; name: string }[]) => void
): Promise<void> {
  const response = await fetch(`${API_BASE}/api/ai/chat/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, history }),
  })

  if (!response.body) throw new Error('No response body')

  const reader = response.body.getReader()
  const decoder = new TextDecoder()

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    const chunk = decoder.decode(value)
    const lines = chunk.split('\n')

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try {
          const json = JSON.parse(line.slice(6))
          if (json.type === 'chunk') {
            onChunk(json.content)
          } else if (json.type === 'done') {
            onComplete(json.files)
          }
        } catch {}
      }
    }
  }
}

// MQL5 Generator
export async function generateMQL5EA(config: MQL5Config): Promise<{
  code: string
  filename: string
  path: string
}> {
  const { data } = await apiClient.post('/api/mql5/generate', config)
  return data
}

export async function installToMT5(filename: string): Promise<{ success: boolean; message: string }> {
  const { data } = await apiClient.post('/api/mql5/install', { filename })
  return data
}

export async function getMQL5Files(): Promise<{ name: string; path: string; size: number; modified: string }[]> {
  const { data } = await apiClient.get('/api/mql5/files')
  return data
}

// Telegram
export async function configureTelegram(config: TelegramConfig): Promise<{ success: boolean }> {
  const { data } = await apiClient.post('/api/telegram/config', config)
  return data
}

export async function testTelegram(): Promise<{ success: boolean; message: string }> {
  const { data } = await apiClient.post('/api/telegram/test')
  return data
}

export async function getTelegramConfig(): Promise<TelegramConfig> {
  const { data } = await apiClient.get('/api/telegram/config')
  return data
}

// TradingView
export async function getTradingViewSignals(): Promise<TradingViewSignal[]> {
  const { data } = await apiClient.get('/api/tradingview/signals')
  return data
}

export async function getTradingViewWebhookUrl(): Promise<{ url: string; secret: string }> {
  const { data } = await apiClient.get('/api/tradingview/webhook')
  return data
}

export async function updateWebhookSecret(secret: string): Promise<{ success: boolean }> {
  const { data } = await apiClient.post('/api/tradingview/webhook/secret', { secret })
  return data
}

// Risk Management
export async function getRiskMetrics(): Promise<RiskMetrics> {
  const { data } = await apiClient.get('/api/risk/metrics')
  return data
}

export async function updateRiskSettings(settings: Partial<RiskMetrics>): Promise<RiskMetrics> {
  const { data } = await apiClient.put('/api/risk/settings', settings)
  return data
}

export async function emergencyStop(): Promise<{ success: boolean; message: string }> {
  const { data } = await apiClient.post('/api/risk/emergency-stop')
  return data
}

export async function calculatePositionSize(params: {
  symbol: string
  riskPercent: number
  stopLossPips: number
  accountBalance: number
}): Promise<{ lots: number; riskAmount: number }> {
  const { data } = await apiClient.post('/api/risk/position-size', params)
  return data
}

export default apiClient
