const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = 'ApiError';
  }
}

async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE}${endpoint}`;
  const config: RequestInit = {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  };

  try {
    const response = await fetch(url, config);
    if (!response.ok) {
      throw new ApiError(response.status, `HTTP ${response.status}: ${response.statusText}`);
    }
    return response.json();
  } catch (error) {
    if (error instanceof ApiError) throw error;
    throw new ApiError(0, `Network error: ${(error as Error).message}`);
  }
}

export const api = {
  account: {
    getInfo: () => request<import('@/types').AccountInfo>('/api/account'),
    getEquityCurve: (period?: string) =>
      request<import('@/types').EquityPoint[]>(`/api/account/equity?period=${period || '1M'}`),
  },

  trades: {
    getHistory: (limit = 50) =>
      request<import('@/types').Trade[]>(`/api/trades/history?limit=${limit}`),
    getOpen: () =>
      request<import('@/types').OpenPosition[]>('/api/trades/open'),
    close: (ticket: number) =>
      request<{ success: boolean }>(`/api/trades/${ticket}/close`, { method: 'POST' }),
    place: (order: {
      symbol: string;
      type: 'BUY' | 'SELL';
      volume: number;
      stopLoss?: number;
      takeProfit?: number;
    }) => request<{ ticket: number }>('/api/trades/place', {
      method: 'POST',
      body: JSON.stringify(order),
    }),
  },

  strategies: {
    getAll: () => request<import('@/types').Strategy[]>('/api/strategies'),
    get: (id: string) => request<import('@/types').Strategy>(`/api/strategies/${id}`),
    toggle: (id: string, active: boolean) =>
      request<import('@/types').Strategy>(`/api/strategies/${id}/toggle`, {
        method: 'POST',
        body: JSON.stringify({ active }),
      }),
    create: (strategy: Partial<import('@/types').Strategy>) =>
      request<import('@/types').Strategy>('/api/strategies', {
        method: 'POST',
        body: JSON.stringify(strategy),
      }),
  },

  performance: {
    getMetrics: () =>
      request<import('@/types').PerformanceMetrics>('/api/performance/metrics'),
  },

  ai: {
    getStatus: () => request<import('@/types').AIModelStatus>('/api/ai/status'),
    chat: (message: string) =>
      request<import('@/types').ChatMessage>('/api/ai/chat', {
        method: 'POST',
        body: JSON.stringify({ message }),
      }),
    train: () => request<{ status: string }>('/api/ai/train', { method: 'POST' }),
  },

  market: {
    getData: () => request<import('@/types').MarketData[]>('/api/market/data'),
    getRegime: () => request<import('@/types').MarketRegime>('/api/market/regime'),
  },

  backtest: {
    run: (config: import('@/types').BacktestConfig) =>
      request<import('@/types').BacktestResult>('/api/backtest/run', {
        method: 'POST',
        body: JSON.stringify(config),
      }),
  },

  settings: {
    get: () => request<import('@/types').Settings>('/api/settings'),
    update: (settings: Partial<import('@/types').Settings>) =>
      request<import('@/types').Settings>('/api/settings', {
        method: 'PUT',
        body: JSON.stringify(settings),
      }),
  },

  status: {
    getConnections: () =>
      request<import('@/types').ConnectionStatus>('/api/status/connections'),
  },
};
