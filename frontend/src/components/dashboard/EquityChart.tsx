'use client';

import { useState } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Area,
  AreaChart,
} from 'recharts';
import { cn } from '@/lib/utils';
import type { EquityPoint } from '@/types';

function generateMockEquityData(): EquityPoint[] {
  const data: EquityPoint[] = [];
  let balance = 45000;
  let equity = 45000;
  const now = new Date();

  for (let i = 90; i >= 0; i--) {
    const date = new Date(now);
    date.setDate(date.getDate() - i);

    const dailyReturn = (Math.random() - 0.42) * 400;
    balance += dailyReturn > 0 ? dailyReturn * 0.8 : dailyReturn * 0.5;
    equity = balance + (Math.random() - 0.5) * 200;

    data.push({
      timestamp: date.toISOString(),
      equity: Math.round(equity * 100) / 100,
      balance: Math.round(balance * 100) / 100,
    });
  }

  return data;
}

const mockData = generateMockEquityData();

const periods = ['1W', '1M', '3M', '6M', '1Y', 'ALL'] as const;

interface CustomTooltipProps {
  active?: boolean;
  payload?: Array<{ value: number; dataKey: string; color: string }>;
  label?: string;
}

function CustomTooltip({ active, payload, label }: CustomTooltipProps) {
  if (!active || !payload) return null;

  return (
    <div className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 shadow-xl">
      <p className="text-xs text-slate-400">
        {new Date(label || '').toLocaleDateString('en-US', {
          month: 'short',
          day: 'numeric',
          year: 'numeric',
        })}
      </p>
      {payload.map((entry) => (
        <p key={entry.dataKey} className="text-sm font-semibold" style={{ color: entry.color }}>
          {entry.dataKey === 'equity' ? 'Equity' : 'Balance'}:{' '}
          ${entry.value.toLocaleString('en-US', { minimumFractionDigits: 2 })}
        </p>
      ))}
    </div>
  );
}

export function EquityChart() {
  const [period, setPeriod] = useState<(typeof periods)[number]>('3M');

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/30 p-5">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-400">
          Equity Curve
        </h3>
        <div className="flex gap-1 rounded-lg bg-slate-800/50 p-0.5">
          {periods.map((p) => (
            <button
              key={p}
              onClick={() => setPeriod(p)}
              className={cn(
                'rounded-md px-2.5 py-1 text-xs font-medium transition-all',
                period === p
                  ? 'bg-slate-700 text-slate-100'
                  : 'text-slate-500 hover:text-slate-300'
              )}
            >
              {p}
            </button>
          ))}
        </div>
      </div>

      <div className="h-72">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={mockData}>
            <defs>
              <linearGradient id="equityGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#34d399" stopOpacity={0.2} />
                <stop offset="100%" stopColor="#34d399" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="balanceGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#60a5fa" stopOpacity={0.1} />
                <stop offset="100%" stopColor="#60a5fa" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
            <XAxis
              dataKey="timestamp"
              tickFormatter={(val) =>
                new Date(val).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
              }
              stroke="#475569"
              tick={{ fill: '#64748b', fontSize: 11 }}
              axisLine={{ stroke: '#334155' }}
            />
            <YAxis
              stroke="#475569"
              tick={{ fill: '#64748b', fontSize: 11 }}
              axisLine={{ stroke: '#334155' }}
              tickFormatter={(val) => `$${(val / 1000).toFixed(0)}k`}
            />
            <Tooltip content={<CustomTooltip />} />
            <Area
              type="monotone"
              dataKey="balance"
              stroke="#60a5fa"
              strokeWidth={1.5}
              fill="url(#balanceGradient)"
              dot={false}
            />
            <Area
              type="monotone"
              dataKey="equity"
              stroke="#34d399"
              strokeWidth={2}
              fill="url(#equityGradient)"
              dot={false}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      <div className="mt-3 flex items-center justify-center gap-6">
        <div className="flex items-center gap-2">
          <div className="h-0.5 w-4 rounded bg-emerald-400" />
          <span className="text-xs text-slate-500">Equity</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="h-0.5 w-4 rounded bg-blue-400" />
          <span className="text-xs text-slate-500">Balance</span>
        </div>
      </div>
    </div>
  );
}
