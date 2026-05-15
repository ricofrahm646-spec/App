export interface Trade {
  ticket: number
  symbol: string
  type: 'BUY' | 'SELL'
  lots: number
  openPrice: number
  currentPrice: number
  stopLoss: number
  takeProfit: number
  profit: number
  openTime: string
  comment: string
}

export interface Strategy {
  id: number
  name: string
  type: string
  status: 'ACTIVE' | 'INACTIVE' | 'TESTING'
  winrate: number
  profitFactor: number
  totalTrades: number
  description: string
}

export interface AccountInfo {
  balance: number
  equity: number
  margin: number
  freeMargin: number
  marginLevel: number
  profit: number
  currency: string
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: string
  files?: GeneratedFile[]
}

export interface GeneratedFile {
  path: string
  type: 'mql5' | 'python' | 'json'
  name: string
  installed?: boolean
}

export interface BacktestResult {
  totalTrades: number
  winTrades: number
  lossTrades: number
  winrate: number
  profitFactor: number
  totalProfit: number
  maxDrawdown: number
  sharpeRatio: number
  equityCurve: number[]
  trades: Trade[]
}

export interface RiskMetrics {
  currentDrawdown: number
  maxDrawdown: number
  dailyPnL: number
  riskPerTrade: number
  positionSize: number
  stopTrading: boolean
}

export interface TradingViewSignal {
  id: number
  symbol: string
  action: 'BUY' | 'SELL'
  price: number
  stopLoss: number
  takeProfit: number
  strategy: string
  timestamp: string
  processed: boolean
}

export interface DashboardData {
  balance: number
  equity: number
  profit: number
  winrate: number
  openTrades: number
  drawdown: number
  equityCurve: { time: string; value: number }[]
  recentTrades: Trade[]
}

export interface OrderRequest {
  symbol: string
  type: 'BUY' | 'SELL'
  lots: number
  stopLoss?: number
  takeProfit?: number
  comment?: string
}

export interface BacktestRequest {
  strategyId: number
  symbol: string
  timeframe: string
  startDate: string
  endDate: string
  initialBalance: number
}

export interface MQL5Config {
  strategyType: string
  name: string
  symbol: string
  timeframe: string
  riskPercent: number
  stopLoss: number
  takeProfit: number
  magicNumber: number
  parameters: Record<string, string | number | boolean>
}

export interface TelegramConfig {
  botToken: string
  chatId: string
  enabled: boolean
  sendTrades: boolean
  sendAlerts: boolean
  sendDailyReport: boolean
}

export interface ConnectionStatus {
  mt5: boolean
  ai: boolean
  telegram: boolean
  websocket: boolean
}
