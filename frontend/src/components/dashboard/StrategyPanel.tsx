'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { formatPercent, formatNumber, cn } from '@/lib/utils';
import type { Strategy } from '@/lib/api';
import * as Switch from '@radix-ui/react-switch';
import { Zap, Bot } from 'lucide-react';

interface StrategyPanelProps {
  strategies: Strategy[];
  onToggle?: (id: number, active: boolean) => void;
}

export default function StrategyPanel({ strategies, onToggle }: StrategyPanelProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base text-white">Strategies</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {strategies.length === 0 ? (
          <p className="py-8 text-center text-sm text-slate-500">No strategies configured</p>
        ) : (
          strategies.map((strategy) => (
            <div
              key={strategy.id}
              className={cn(
                'rounded-lg border p-4 transition-all',
                strategy.is_active
                  ? 'border-blue-500/30 bg-blue-950/10'
                  : 'border-slate-700/30 bg-slate-800/30'
              )}
            >
              <div className="mb-3 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  {strategy.type === 'scalping' ? (
                    <Zap className="h-4 w-4 text-amber-400" />
                  ) : (
                    <Bot className="h-4 w-4 text-blue-400" />
                  )}
                  <span className="font-medium text-white">{strategy.name}</span>
                  <span className="rounded-md bg-slate-700/50 px-2 py-0.5 text-xs text-slate-400">
                    {strategy.type}
                  </span>
                </div>
                <Switch.Root
                  checked={strategy.is_active}
                  onCheckedChange={(checked) => onToggle?.(strategy.id, checked)}
                  className={cn(
                    'relative h-5 w-9 rounded-full transition-colors',
                    strategy.is_active ? 'bg-blue-500' : 'bg-slate-600'
                  )}
                >
                  <Switch.Thumb className="block h-4 w-4 translate-x-0.5 rounded-full bg-white transition-transform data-[state=checked]:translate-x-[18px]" />
                </Switch.Root>
              </div>

              <div className="grid grid-cols-3 gap-3 text-xs">
                <div>
                  <span className="text-slate-500">Winrate</span>
                  <div className="mt-1">
                    <div className="mb-1 font-medium text-white">
                      {formatPercent(strategy.winrate)}
                    </div>
                    <div className="h-1.5 overflow-hidden rounded-full bg-slate-700">
                      <div
                        className="h-full rounded-full bg-emerald-500 transition-all"
                        style={{ width: `${strategy.winrate * 100}%` }}
                      />
                    </div>
                  </div>
                </div>
                <div>
                  <span className="text-slate-500">PF</span>
                  <p className="mt-1 font-medium text-white">
                    {formatNumber(strategy.profit_factor)}
                  </p>
                </div>
                <div>
                  <span className="text-slate-500">Trades</span>
                  <p className="mt-1 font-medium text-white">{strategy.total_trades}</p>
                </div>
              </div>
            </div>
          ))
        )}
      </CardContent>
    </Card>
  );
}
