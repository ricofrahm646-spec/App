'use client';

import { AccountOverview } from '@/components/dashboard/AccountOverview';
import { PerformanceMetrics } from '@/components/dashboard/PerformanceMetrics';
import { EquityChart } from '@/components/dashboard/EquityChart';
import { TradeHistory } from '@/components/dashboard/TradeHistory';
import { OpenPositions } from '@/components/dashboard/OpenPositions';
import { AIStatus } from '@/components/dashboard/AIStatus';
import { StrategyStatus } from '@/components/dashboard/StrategyStatus';
import { MarketAnalysis } from '@/components/dashboard/MarketAnalysis';

export default function DashboardPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-100">
            Dashboard
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            Real-time trading overview and performance metrics
          </p>
        </div>
        <div className="flex items-center gap-2 text-xs text-slate-500">
          <div className="h-2 w-2 rounded-full bg-emerald-400 pulse-dot" />
          Live
        </div>
      </div>

      <AccountOverview />

      <PerformanceMetrics />

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <EquityChart />
        </div>
        <div>
          <AIStatus />
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <OpenPositions />
        <MarketAnalysis />
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <TradeHistory />
        </div>
        <div>
          <StrategyStatus />
        </div>
      </div>
    </div>
  );
}
