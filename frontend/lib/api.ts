import type { ChatResponse, DashboardMetric } from "@/lib/types";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export async function sendChatMessage(message: string): Promise<ChatResponse> {
  const response = await fetch(`${API_BASE_URL}/api/chat/message`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  });

  if (!response.ok) {
    throw new Error("Chat request failed");
  }
  return response.json();
}

export async function fetchDashboardMetrics(): Promise<DashboardMetric[]> {
  // Initial static KPIs; replace with live websocket stream in next iteration.
  return [
    { label: "Balance", value: "10,000.00 USD", trend: "+0.8%" },
    { label: "Equity", value: "10,120.50 USD", trend: "+1.2%" },
    { label: "Margin", value: "532.30 USD" },
    { label: "Winrate", value: "54.5%" },
    { label: "Profit Factor", value: "1.32" },
    { label: "Drawdown", value: "11.8%" },
    { label: "Open Trades", value: "1" },
    { label: "KI Status", value: "Active" },
  ];
}
