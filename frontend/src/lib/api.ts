const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';
const WS_BASE = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000';

export interface Trade {
  id: number;
  symbol: string;
  direction: string;
  volume: number;
  open_price: number;
  close_price: number | null;
  sl: number | null;
  tp: number | null;
  open_time: string;
  close_time: string | null;
  profit: number;
  status: string;
  strategy_name: string;
}

export interface AccountInfo {
  balance: number;
  equity: number;
  margin: number;
  free_margin: number;
  profit: number;
}

export interface DashboardData {
  account: AccountInfo;
  stats: {
    total_trades: number;
    winning_trades: number;
    losing_trades: number;
    winrate: number;
    profit_factor: number;
    max_drawdown: number;
    total_profit: number;
  };
  open_trades: Trade[];
  recent_trades: Trade[];
  strategies: Strategy[];
}

export interface Strategy {
  id: number;
  name: string;
  type: string;
  is_active: boolean;
  winrate: number;
  profit_factor: number;
  total_trades: number;
}

export interface ChatMessage {
  id?: number;
  role: 'user' | 'assistant';
  content: string;
  metadata?: Record<string, unknown>;
  created_at?: string;
}

class JarvisAPI {
  private baseUrl: string;

  constructor() {
    this.baseUrl = API_BASE;
  }

  private async request<T>(path: string, options?: RequestInit): Promise<T> {
    const res = await fetch(`${this.baseUrl}${path}`, {
      headers: { 'Content-Type': 'application/json', ...options?.headers },
      ...options,
    });
    if (!res.ok) throw new Error(`API Error: ${res.status}`);
    return res.json();
  }

  async getDashboard(): Promise<DashboardData> {
    return this.request('/account/dashboard');
  }

  async getAccountInfo(): Promise<AccountInfo> {
    return this.request('/account/info');
  }

  async getTrades(): Promise<Trade[]> {
    return this.request('/trades');
  }

  async getOpenTrades(): Promise<Trade[]> {
    return this.request('/trades/open');
  }

  async openTrade(data: { symbol: string; direction: string; volume: number; sl?: number; tp?: number }): Promise<Trade> {
    return this.request('/trades/open', { method: 'POST', body: JSON.stringify(data) });
  }

  async closeTrade(id: number): Promise<{ success: boolean }> {
    return this.request(`/trades/${id}/close`, { method: 'POST' });
  }

  async getStrategies(): Promise<Strategy[]> {
    return this.request('/strategies');
  }

  async sendChatMessage(content: string): Promise<ChatMessage> {
    return this.request('/chat/message', { method: 'POST', body: JSON.stringify({ content }) });
  }

  async getChatHistory(): Promise<ChatMessage[]> {
    return this.request('/chat/history');
  }

  async getTradeStats(): Promise<Record<string, number>> {
    return this.request('/trades/stats');
  }

  async connectMT5(config: { path?: string; login?: number; password?: string; server?: string }): Promise<{ success: boolean }> {
    return this.request('/mt5/connect', { method: 'POST', body: JSON.stringify(config) });
  }

  async getMT5Status(): Promise<{ connected: boolean; account?: string }> {
    return this.request('/mt5/status');
  }

  async updateSettings(section: string, data: Record<string, unknown>): Promise<{ success: boolean }> {
    return this.request(`/settings/${section}`, { method: 'PUT', body: JSON.stringify(data) });
  }

  createWebSocket(path: string): WebSocket {
    return new WebSocket(`${WS_BASE}${path}`);
  }
}

export const api = new JarvisAPI();
