export interface AccountInfo {
  balance: number;
  equity: number;
  margin: number;
  freeMargin: number;
  marginLevel: number;
  profit: number;
  currency: string;
}

export interface Trade {
  id: string;
  ticket: number;
  symbol: string;
  type: 'BUY' | 'SELL';
  volume: number;
  openPrice: number;
  closePrice: number | null;
  stopLoss: number | null;
  takeProfit: number | null;
  profit: number;
  commission: number;
  swap: number;
  openTime: string;
  closeTime: string | null;
  comment: string;
}

export interface OpenPosition {
  ticket: number;
  symbol: string;
  type: 'BUY' | 'SELL';
  volume: number;
  openPrice: number;
  currentPrice: number;
  stopLoss: number | null;
  takeProfit: number | null;
  profit: number;
  swap: number;
  openTime: string;
}

export interface PerformanceMetrics {
  totalTrades: number;
  winRate: number;
  profitFactor: number;
  wins: number;
  losses: number;
  maxDrawdown: number;
  dailyPnL: number;
  weeklyPnL: number;
  monthlyPnL: number;
  sharpeRatio: number;
  averageWin: number;
  averageLoss: number;
}

export interface EquityPoint {
  timestamp: string;
  equity: number;
  balance: number;
}

export interface Strategy {
  id: string;
  name: string;
  type: 'AI' | 'Technical' | 'Hybrid' | 'Manual';
  status: 'active' | 'paused' | 'disabled';
  description: string;
  winRate: number;
  profitFactor: number;
  totalTrades: number;
  profit: number;
  symbols: string[];
  timeframe: string;
  createdAt: string;
  lastUpdated: string;
}

export interface AIModelStatus {
  modelName: string;
  status: 'trained' | 'training' | 'idle' | 'error';
  activeStrategy: string;
  lastPrediction: {
    symbol: string;
    direction: 'BUY' | 'SELL' | 'HOLD';
    confidence: number;
    timestamp: string;
  } | null;
  accuracy: number;
  trainingProgress: number;
  lastTrainedAt: string | null;
}

export interface MarketData {
  symbol: string;
  bid: number;
  ask: number;
  spread: number;
  change: number;
  changePercent: number;
  high: number;
  low: number;
  volume: number;
}

export interface MarketRegime {
  regime: 'trending_up' | 'trending_down' | 'ranging' | 'volatile';
  confidence: number;
  session: 'asian' | 'london' | 'new_york' | 'overlap';
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  actions?: ChatAction[];
}

export interface ChatAction {
  type: 'file_created' | 'trade_executed' | 'strategy_updated' | 'analysis';
  description: string;
  data?: Record<string, unknown>;
}

export interface BacktestConfig {
  strategyId: string;
  symbol: string;
  timeframe: string;
  startDate: string;
  endDate: string;
  initialBalance: number;
  riskPerTrade: number;
}

export interface BacktestResult {
  totalTrades: number;
  winRate: number;
  profitFactor: number;
  totalProfit: number;
  maxDrawdown: number;
  sharpeRatio: number;
  equityCurve: EquityPoint[];
  trades: Trade[];
}

export interface ConnectionStatus {
  mt5: boolean;
  redis: boolean;
  database: boolean;
  websocket: boolean;
}

export interface Settings {
  mt5: {
    server: string;
    login: string;
    password: string;
    path: string;
  };
  telegram: {
    token: string;
    chatId: string;
    enabled: boolean;
  };
  tradingview: {
    webhookUrl: string;
    secretKey: string;
    enabled: boolean;
  };
  risk: {
    maxRiskPerTrade: number;
    maxDailyDrawdown: number;
    maxOpenPositions: number;
    defaultLotSize: number;
  };
  ai: {
    modelType: string;
    retrainInterval: number;
    minConfidence: number;
    features: string[];
  };
}

export interface Notification {
  id: string;
  type: 'info' | 'warning' | 'error' | 'success' | 'trade';
  title: string;
  message: string;
  timestamp: string;
  read: boolean;
}

export interface WebSocketMessage {
  channel: string;
  event: string;
  data: unknown;
}
