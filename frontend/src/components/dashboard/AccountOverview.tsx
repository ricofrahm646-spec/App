'use client';

import { useState, useEffect } from 'react';
import { Wallet, TrendingUp, Shield, DollarSign } from 'lucide-react';
import { cn, formatCurrency, profitColor } from '@/lib/utils';
import type { AccountInfo } from '@/types';

const mockAccount: AccountInfo = {
  balance: 52847.32,
  equity: 53291.18,
  margin: 4230.50,
  freeMargin: 49060.68,
  marginLevel: 1260.42,
  profit: 443.86,
  currency: 'USD',
};

interface StatCardProps {
  label: string;
  value: string;
  icon: React.ReactNode;
  change?: number;
  className?: string;
}

function StatCard({ label, value, icon, change, className }: StatCardProps) {
  return (
    <div className={cn('rounded-xl border border-slate-800 bg-slate-900/50 p-4', className)}>
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium uppercase tracking-wider text-slate-500">
          {label}
        </span>
        <div className="rounded-lg bg-slate-800/50 p-1.5">{icon}</div>
      </div>
      <p className="mt-2 text-2xl font-bold tracking-tight text-slate-100">
        {value}
      </p>
      {change !== undefined && (
        <p className={cn('mt-1 text-xs font-medium', profitColor(change))}>
          {change >= 0 ? '+' : ''}{formatCurrency(change)}
        </p>
      )}
    </div>
  );
}

export function AccountOverview() {
  const [account, setAccount] = useState<AccountInfo>(mockAccount);

  useEffect(() => {
    const interval = setInterval(() => {
      setAccount((prev) => {
        const delta = (Math.random() - 0.48) * 15;
        const newProfit = prev.profit + delta;
        return {
          ...prev,
          equity: prev.balance + newProfit,
          profit: newProfit,
          freeMargin: prev.balance + newProfit - prev.margin,
        };
      });
    }, 3000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
      <StatCard
        label="Balance"
        value={formatCurrency(account.balance)}
        icon={<Wallet className="h-4 w-4 text-blue-400" />}
      />
      <StatCard
        label="Equity"
        value={formatCurrency(account.equity)}
        icon={<TrendingUp className="h-4 w-4 text-emerald-400" />}
        change={account.profit}
      />
      <StatCard
        label="Margin"
        value={formatCurrency(account.margin)}
        icon={<Shield className="h-4 w-4 text-amber-400" />}
      />
      <StatCard
        label="Free Margin"
        value={formatCurrency(account.freeMargin)}
        icon={<DollarSign className="h-4 w-4 text-purple-400" />}
      />
    </div>
  );
}
