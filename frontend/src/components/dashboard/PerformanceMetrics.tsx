'use client';

import {
  Target,
  TrendingUp,
  BarChart3,
  Award,
  AlertTriangle,
  Calendar,
} from 'lucide-react';
import { cn, formatPercentage, formatCurrency, profitColor } from '@/lib/utils';
import type { PerformanceMetrics as PerformanceMetricsType } from '@/types';

const mockMetrics: PerformanceMetricsType = {
  totalTrades: 347,
  winRate: 68.3,
  profitFactor: 2.14,
  wins: 237,
  losses: 110,
  maxDrawdown: 4.2,
  dailyPnL: 312.45,
  weeklyPnL: 1847.20,
  monthlyPnL: 5234.80,
  sharpeRatio: 1.87,
  averageWin: 87.32,
  averageLoss: -42.18,
};

interface MetricItemProps {
  label: string;
  value: string;
  icon: React.ReactNode;
  subtext?: string;
  highlight?: 'green' | 'red' | 'amber' | 'blue' | 'default';
}

function MetricItem({ label, value, icon, subtext, highlight = 'default' }: MetricItemProps) {
  const highlightColors = {
    green: 'border-emerald-500/20 bg-emerald-500/5',
    red: 'border-red-500/20 bg-red-500/5',
    amber: 'border-amber-500/20 bg-amber-500/5',
    blue: 'border-blue-500/20 bg-blue-500/5',
    default: 'border-slate-800 bg-slate-900/50',
  };

  return (
    <div
      className={cn(
        'rounded-xl border p-4 transition-all hover:border-slate-700',
        highlightColors[highlight]
      )}
    >
      <div className="flex items-center gap-2">
        {icon}
        <span className="text-xs font-medium uppercase tracking-wider text-slate-500">
          {label}
        </span>
      </div>
      <p className="mt-2 text-xl font-bold text-slate-100">{value}</p>
      {subtext && (
        <p className="mt-0.5 text-xs text-slate-500">{subtext}</p>
      )}
    </div>
  );
}

export function PerformanceMetrics() {
  const metrics = mockMetrics;

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/30 p-5">
      <h3 className="mb-4 text-sm font-semibold uppercase tracking-wider text-slate-400">
        Performance Metrics
      </h3>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-6">
        <MetricItem
          label="Win Rate"
          value={`${metrics.winRate}%`}
          icon={<Target className="h-4 w-4 text-emerald-400" />}
          subtext={`${metrics.wins}W / ${metrics.losses}L`}
          highlight="green"
        />
        <MetricItem
          label="Profit Factor"
          value={metrics.profitFactor.toFixed(2)}
          icon={<TrendingUp className="h-4 w-4 text-blue-400" />}
          subtext="Ratio W/L"
          highlight="blue"
        />
        <MetricItem
          label="Total Trades"
          value={metrics.totalTrades.toString()}
          icon={<BarChart3 className="h-4 w-4 text-purple-400" />}
          subtext="All time"
        />
        <MetricItem
          label="Sharpe Ratio"
          value={metrics.sharpeRatio.toFixed(2)}
          icon={<Award className="h-4 w-4 text-amber-400" />}
          subtext="Risk adjusted"
          highlight="amber"
        />
        <MetricItem
          label="Max Drawdown"
          value={`${metrics.maxDrawdown}%`}
          icon={<AlertTriangle className="h-4 w-4 text-red-400" />}
          subtext="Peak to trough"
          highlight="red"
        />
        <MetricItem
          label="Daily P&L"
          value={formatCurrency(metrics.dailyPnL)}
          icon={<Calendar className="h-4 w-4 text-emerald-400" />}
          subtext={formatCurrency(metrics.weeklyPnL) + ' weekly'}
          highlight="green"
        />
      </div>
    </div>
  );
}
