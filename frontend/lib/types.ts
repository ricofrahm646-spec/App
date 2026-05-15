export type DashboardMetrics = {
  balance: number;
  equity: number;
  margin: number;
  winrate: number;
  totalTrades: number;
  winningTrades: number;
  losingTrades: number;
  profitFactor: number;
  drawdown: number;
  aiStatus: string;
  strategyStatus: string;
};

export type ChatResponse = {
  summary: string;
  actions: string[];
  generated_files: string[];
};
