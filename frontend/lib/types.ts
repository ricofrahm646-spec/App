export type DashboardMetric = {
  label: string;
  value: string;
  trend?: string;
};

export type ChatAction = {
  action: string;
  target_module: string;
  description: string;
};

export type ChatResponse = {
  summary: string;
  actions: ChatAction[];
};
