'use client';

import { useEffect, useState, useCallback, useRef } from 'react';
import { api, type DashboardData } from '@/lib/api';
import StatsCards from '@/components/dashboard/StatsCards';
import EquityChart from '@/components/dashboard/EquityChart';
import TradeTable from '@/components/dashboard/TradeTable';
import StrategyPanel from '@/components/dashboard/StrategyPanel';
import StatusBar from '@/components/dashboard/StatusBar';

interface EquityPoint {
  time: string;
  equity: number;
  balance: number;
}

function generateMockEquity(): EquityPoint[] {
  const points: EquityPoint[] = [];
  let equity = 10000;
  let balance = 10000;
  for (let i = 30; i >= 0; i--) {
    const date = new Date();
    date.setDate(date.getDate() - i);
    equity += (Math.random() - 0.45) * 200;
    balance += (Math.random() - 0.45) * 150;
    points.push({
      time: date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
      equity: Math.round(equity * 100) / 100,
      balance: Math.round(balance * 100) / 100,
    });
  }
  return points;
}

export default function DashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [equityData] = useState<EquityPoint[]>(() => generateMockEquity());
  const [mt5Connected, setMt5Connected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  const fetchDashboard = useCallback(async () => {
    try {
      const dashboard = await api.getDashboard();
      setData(dashboard);
    } catch {
      /* API not available */
    }
  }, []);

  useEffect(() => {
    let cancelled = false;

    api.getDashboard()
      .then((d) => { if (!cancelled) setData(d); })
      .catch(() => {});

    api.getMT5Status()
      .then((s) => { if (!cancelled) setMt5Connected(s.connected); })
      .catch(() => {});

    const interval = setInterval(() => {
      api.getDashboard()
        .then((d) => { if (!cancelled) setData(d); })
        .catch(() => {});
    }, 15000);

    try {
      const ws = api.createWebSocket('/ws/dashboard');
      wsRef.current = ws;
      ws.onmessage = (e) => {
        try {
          const update = JSON.parse(e.data) as Partial<DashboardData>;
          if (!cancelled) setData((prev) => (prev ? { ...prev, ...update } : null));
        } catch {
          /* ignore parse errors */
        }
      };
    } catch {
      /* WebSocket not available */
    }

    return () => {
      cancelled = true;
      clearInterval(interval);
      wsRef.current?.close();
    };
  }, []);

  const activeStrategies = data?.strategies.filter((s) => s.is_active).length ?? 0;

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Dashboard</h1>
          <p className="text-sm text-slate-400">Real-time trading overview</p>
        </div>
      </div>

      <StatusBar mt5Connected={mt5Connected} activeStrategies={activeStrategies} />
      <StatsCards data={data} />

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
        <div className="xl:col-span-2">
          <EquityChart data={equityData} />
        </div>
        <div>
          <StrategyPanel strategies={data?.strategies ?? []} />
        </div>
      </div>

      <TradeTable
        trades={data?.open_trades ?? []}
        title="Open Trades"
        showClose
        onTradeClose={fetchDashboard}
      />

      <TradeTable trades={data?.recent_trades ?? []} title="Recent Trades" />
    </div>
  );
}
