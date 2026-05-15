export type MetricCard = {
  label: string;
  value: string;
  detail: string;
};

export type ModuleStatus = {
  name: string;
  status: "healthy" | "degraded" | "pending";
  description: string;
};

export type TradeSnapshot = {
  symbol: string;
  direction: "buy" | "sell";
  entry_price: number;
  stop_loss: number;
  take_profit: number;
  strategy: string;
  state: "open" | "closed" | "draft";
};

export type SystemOverview = {
  metrics: MetricCard[];
  modules: ModuleStatus[];
  open_trades: TradeSnapshot[];
  active_strategy: string;
  ai_status: string;
};

export type GeneratedArtifact = {
  path: string;
  kind: "python" | "mql5" | "markdown" | "json" | "yaml";
  summary: string;
};

export type ChatCommandResponse = {
  intent: string;
  acknowledgement: string;
  plan: {
    title: string;
    description: string;
    actions: string[];
    generated_artifacts: GeneratedArtifact[];
    risk_notes: string[];
  };
  created_files: string[];
  created_at: string;
};

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

const fallbackOverview: SystemOverview = {
  metrics: [
    { label: "Balance", value: "$100,000", detail: "Paper baseline" },
    { label: "Equity", value: "$100,000", detail: "No live exposure" },
    { label: "Winrate", value: "N/A", detail: "Requires validated backtests" },
    { label: "Drawdown Limit", value: "20%", detail: "Emergency threshold" },
  ],
  modules: [
    {
      name: "AI Planner",
      status: "healthy",
      description: "Intent orchestration available",
    },
    {
      name: "MT5 Connector",
      status: "pending",
      description: "Needs local terminal access",
    },
    {
      name: "Risk Engine",
      status: "healthy",
      description: "Single-trade policy active",
    },
  ],
  open_trades: [],
  active_strategy: "No active live strategy",
  ai_status: "Ready for command intake",
};

export async function fetchOverview(): Promise<SystemOverview> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/system/overview`, {
      cache: "no-store",
    });
    if (!response.ok) {
      throw new Error("Unable to load overview");
    }

    return (await response.json()) as SystemOverview;
  } catch {
    return fallbackOverview;
  }
}

export async function runChatCommand(
  message: string,
): Promise<ChatCommandResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/chat/command`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ message }),
  });

  if (!response.ok) {
    throw new Error("JARVIS could not process the command.");
  }

  return (await response.json()) as ChatCommandResponse;
}
