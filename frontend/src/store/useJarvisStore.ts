import { create } from 'zustand'
import {
  AccountInfo,
  Trade,
  Strategy,
  ChatMessage,
  DashboardData,
  RiskMetrics,
  TradingViewSignal,
  ConnectionStatus,
} from '@/types'

interface JarvisStore {
  // State
  accountInfo: AccountInfo
  openTrades: Trade[]
  strategies: Strategy[]
  chatHistory: ChatMessage[]
  dashboardData: DashboardData
  riskMetrics: RiskMetrics
  tradingViewSignals: TradingViewSignal[]
  connectionStatus: ConnectionStatus
  aiStatus: 'idle' | 'thinking' | 'error'
  selectedSection: string
  isLoading: boolean

  // Account Actions
  setAccountInfo: (info: AccountInfo) => void
  updateAccountInfo: (partial: Partial<AccountInfo>) => void

  // Trade Actions
  setOpenTrades: (trades: Trade[]) => void
  addTrade: (trade: Trade) => void
  removeTrade: (ticket: number) => void
  updateTrade: (ticket: number, partial: Partial<Trade>) => void

  // Strategy Actions
  setStrategies: (strategies: Strategy[]) => void
  updateStrategy: (id: number, partial: Partial<Strategy>) => void
  addStrategy: (strategy: Strategy) => void

  // Chat Actions
  setChatHistory: (messages: ChatMessage[]) => void
  addMessage: (message: ChatMessage) => void
  clearChat: () => void
  setAiStatus: (status: 'idle' | 'thinking' | 'error') => void

  // Dashboard Actions
  setDashboardData: (data: DashboardData) => void
  updateDashboardData: (partial: Partial<DashboardData>) => void

  // Risk Actions
  setRiskMetrics: (metrics: RiskMetrics) => void

  // TradingView Actions
  setTradingViewSignals: (signals: TradingViewSignal[]) => void
  addTradingViewSignal: (signal: TradingViewSignal) => void

  // Connection Actions
  setConnectionStatus: (status: Partial<ConnectionStatus>) => void
  setMT5Status: (connected: boolean) => void
  setTelegramStatus: (connected: boolean) => void
  setAIStatus: (connected: boolean) => void
  setWebSocketStatus: (connected: boolean) => void

  // UI Actions
  setSelectedSection: (section: string) => void
  setLoading: (loading: boolean) => void
}

const mockEquityCurve = Array.from({ length: 30 }, (_, i) => ({
  time: new Date(Date.now() - (29 - i) * 24 * 60 * 60 * 1000).toLocaleDateString(),
  value: 10000 + Math.random() * 2000 - 500 + i * 80,
}))

const mockTrades: Trade[] = [
  {
    ticket: 123456,
    symbol: 'XAUUSD',
    type: 'BUY',
    lots: 0.1,
    openPrice: 2315.50,
    currentPrice: 2318.20,
    stopLoss: 2305.00,
    takeProfit: 2340.00,
    profit: 27.0,
    openTime: new Date(Date.now() - 3600000).toISOString(),
    comment: 'ICT_Strategy_v2',
  },
  {
    ticket: 123457,
    symbol: 'EURUSD',
    type: 'SELL',
    lots: 0.5,
    openPrice: 1.08450,
    currentPrice: 1.08320,
    stopLoss: 1.08700,
    takeProfit: 1.08000,
    profit: 65.0,
    openTime: new Date(Date.now() - 7200000).toISOString(),
    comment: 'Trend_Follow_EA',
  },
  {
    ticket: 123458,
    symbol: 'GBPUSD',
    type: 'BUY',
    lots: 0.2,
    openPrice: 1.26780,
    currentPrice: 1.26650,
    stopLoss: 1.26400,
    takeProfit: 1.27200,
    profit: -26.0,
    openTime: new Date(Date.now() - 1800000).toISOString(),
    comment: 'Scalper_Bot',
  },
]

const mockStrategies: Strategy[] = [
  {
    id: 1,
    name: 'ICT Gold Scalper',
    type: 'ICT',
    status: 'ACTIVE',
    winrate: 68.5,
    profitFactor: 2.34,
    totalTrades: 142,
    description: 'ICT-based gold scalping strategy using order blocks and FVG',
  },
  {
    id: 2,
    name: 'EUR/USD Trend Follower',
    type: 'Trend',
    status: 'ACTIVE',
    winrate: 54.2,
    profitFactor: 1.87,
    totalTrades: 89,
    description: 'Multi-timeframe trend following with EMA crossovers',
  },
  {
    id: 3,
    name: 'GBP Breakout Bot',
    type: 'Breakout',
    status: 'INACTIVE',
    winrate: 61.0,
    profitFactor: 2.10,
    totalTrades: 56,
    description: 'London session breakout strategy for GBP pairs',
  },
  {
    id: 4,
    name: 'News Event Scalper',
    type: 'News',
    status: 'TESTING',
    winrate: 72.0,
    profitFactor: 3.1,
    totalTrades: 28,
    description: 'High-frequency scalping around news events',
  },
]

export const useJarvisStore = create<JarvisStore>((set) => ({
  accountInfo: {
    balance: 12547.83,
    equity: 12614.53,
    margin: 285.40,
    freeMargin: 12329.13,
    marginLevel: 4420.5,
    profit: 66.70,
    currency: 'USD',
  },
  openTrades: mockTrades,
  strategies: mockStrategies,
  chatHistory: [
    {
      id: '1',
      role: 'assistant',
      content: `# JARVIS Online

I'm your AI Trading Assistant. I can help you:

- **Build** custom MQL5 Expert Advisors
- **Analyze** market conditions and strategies
- **Backtest** strategies against historical data
- **Manage** risk and position sizing
- **Monitor** your trading account in real-time

What would you like to do today?`,
      timestamp: new Date().toISOString(),
    },
  ],
  dashboardData: {
    balance: 12547.83,
    equity: 12614.53,
    profit: 66.70,
    winrate: 64.3,
    openTrades: 3,
    drawdown: 2.4,
    equityCurve: mockEquityCurve,
    recentTrades: mockTrades,
  },
  riskMetrics: {
    currentDrawdown: 2.4,
    maxDrawdown: 8.7,
    dailyPnL: 127.50,
    riskPerTrade: 1.0,
    positionSize: 0.1,
    stopTrading: false,
  },
  tradingViewSignals: [
    {
      id: 1,
      symbol: 'XAUUSD',
      action: 'BUY',
      price: 2315.50,
      stopLoss: 2305.00,
      takeProfit: 2340.00,
      strategy: 'ICT Gold',
      timestamp: new Date(Date.now() - 3600000).toISOString(),
      processed: true,
    },
    {
      id: 2,
      symbol: 'EURUSD',
      action: 'SELL',
      price: 1.08450,
      stopLoss: 1.08700,
      takeProfit: 1.08000,
      strategy: 'EUR Trend',
      timestamp: new Date(Date.now() - 7200000).toISOString(),
      processed: true,
    },
  ],
  connectionStatus: {
    mt5: true,
    ai: true,
    telegram: false,
    websocket: true,
  },
  aiStatus: 'idle',
  selectedSection: 'dashboard',
  isLoading: false,

  setAccountInfo: (info) => set({ accountInfo: info }),
  updateAccountInfo: (partial) =>
    set((state) => ({ accountInfo: { ...state.accountInfo, ...partial } })),

  setOpenTrades: (trades) => set({ openTrades: trades }),
  addTrade: (trade) =>
    set((state) => ({ openTrades: [...state.openTrades, trade] })),
  removeTrade: (ticket) =>
    set((state) => ({
      openTrades: state.openTrades.filter((t) => t.ticket !== ticket),
    })),
  updateTrade: (ticket, partial) =>
    set((state) => ({
      openTrades: state.openTrades.map((t) =>
        t.ticket === ticket ? { ...t, ...partial } : t
      ),
    })),

  setStrategies: (strategies) => set({ strategies }),
  updateStrategy: (id, partial) =>
    set((state) => ({
      strategies: state.strategies.map((s) =>
        s.id === id ? { ...s, ...partial } : s
      ),
    })),
  addStrategy: (strategy) =>
    set((state) => ({ strategies: [...state.strategies, strategy] })),

  setChatHistory: (messages) => set({ chatHistory: messages }),
  addMessage: (message) =>
    set((state) => ({ chatHistory: [...state.chatHistory, message] })),
  clearChat: () => set({ chatHistory: [] }),
  setAiStatus: (status) => set({ aiStatus: status }),

  setDashboardData: (data) => set({ dashboardData: data }),
  updateDashboardData: (partial) =>
    set((state) => ({ dashboardData: { ...state.dashboardData, ...partial } })),

  setRiskMetrics: (metrics) => set({ riskMetrics: metrics }),

  setTradingViewSignals: (signals) => set({ tradingViewSignals: signals }),
  addTradingViewSignal: (signal) =>
    set((state) => ({
      tradingViewSignals: [signal, ...state.tradingViewSignals],
    })),

  setConnectionStatus: (status) =>
    set((state) => ({
      connectionStatus: { ...state.connectionStatus, ...status },
    })),
  setMT5Status: (connected) =>
    set((state) => ({
      connectionStatus: { ...state.connectionStatus, mt5: connected },
    })),
  setTelegramStatus: (connected) =>
    set((state) => ({
      connectionStatus: { ...state.connectionStatus, telegram: connected },
    })),
  setAIStatus: (connected) =>
    set((state) => ({
      connectionStatus: { ...state.connectionStatus, ai: connected },
    })),
  setWebSocketStatus: (connected) =>
    set((state) => ({
      connectionStatus: { ...state.connectionStatus, websocket: connected },
    })),

  setSelectedSection: (section) => set({ selectedSection: section }),
  setLoading: (loading) => set({ isLoading: loading }),
}))
