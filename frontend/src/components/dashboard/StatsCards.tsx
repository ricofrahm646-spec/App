'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { formatCurrency, formatPercent, formatNumber } from '@/lib/utils';
import type { DashboardData } from '@/lib/api';
import {
  DollarSign,
  TrendingUp,
  TrendingDown,
  BarChart3,
  Target,
  Shield,
  AlertTriangle,
} from 'lucide-react';

interface StatsCardsProps {
  data: DashboardData | null;
}

export default function StatsCards({ data }: StatsCardsProps) {
  const cards = [
    {
      title: 'Balance',
      value: data ? formatCurrency(data.account.balance) : '—',
      icon: DollarSign,
      color: 'text-blue-400',
      bgColor: 'bg-blue-500/10',
    },
    {
      title: 'Equity',
      value: data ? formatCurrency(data.account.equity) : '—',
      icon: TrendingUp,
      color: 'text-emerald-400',
      bgColor: 'bg-emerald-500/10',
    },
    {
      title: 'Profit',
      value: data ? formatCurrency(data.account.profit) : '—',
      icon: data && data.account.profit >= 0 ? TrendingUp : TrendingDown,
      color: data && data.account.profit >= 0 ? 'text-emerald-400' : 'text-red-400',
      bgColor: data && data.account.profit >= 0 ? 'bg-emerald-500/10' : 'bg-red-500/10',
    },
    {
      title: 'Winrate',
      value: data ? formatPercent(data.stats.winrate) : '—',
      icon: Target,
      color: 'text-violet-400',
      bgColor: 'bg-violet-500/10',
    },
    {
      title: 'Total Trades',
      value: data ? formatNumber(data.stats.total_trades, 0) : '—',
      icon: BarChart3,
      color: 'text-cyan-400',
      bgColor: 'bg-cyan-500/10',
    },
    {
      title: 'Profit Factor',
      value: data ? formatNumber(data.stats.profit_factor) : '—',
      icon: Shield,
      color: 'text-amber-400',
      bgColor: 'bg-amber-500/10',
    },
    {
      title: 'Max Drawdown',
      value: data ? formatPercent(data.stats.max_drawdown) : '—',
      icon: AlertTriangle,
      color: 'text-red-400',
      bgColor: 'bg-red-500/10',
    },
    {
      title: 'Free Margin',
      value: data ? formatCurrency(data.account.free_margin) : '—',
      icon: DollarSign,
      color: 'text-slate-400',
      bgColor: 'bg-slate-500/10',
    },
  ];

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {cards.map((card) => {
        const Icon = card.icon;
        return (
          <Card key={card.title} className="hover:border-slate-600/50 transition-colors">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle>{card.title}</CardTitle>
              <div className={`rounded-lg p-2 ${card.bgColor}`}>
                <Icon className={`h-4 w-4 ${card.color}`} />
              </div>
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-bold text-white">{card.value}</p>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
