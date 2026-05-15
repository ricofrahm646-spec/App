'use client';

import { useEffect, useState } from 'react';
import { api, type Strategy } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { formatPercent, formatNumber, cn } from '@/lib/utils';
import * as Switch from '@radix-ui/react-switch';
import { Bot, Zap, Plus, X, Target, Shield, BarChart3 } from 'lucide-react';

export default function StrategiesPage() {
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({ name: '', type: 'scalping' });
  const [selected, setSelected] = useState<Strategy | null>(null);

  useEffect(() => {
    let cancelled = false;
    api.getStrategies()
      .then((data) => { if (!cancelled) setStrategies(data); })
      .catch(() => {});
    return () => { cancelled = true; };
  }, []);

  const handleToggle = async (id: number, active: boolean) => {
    setStrategies((prev) =>
      prev.map((s) => (s.id === id ? { ...s, is_active: active } : s))
    );
    try {
      await api.updateSettings('strategy', { id, is_active: active });
    } catch {
      setStrategies((prev) =>
        prev.map((s) => (s.id === id ? { ...s, is_active: !active } : s))
      );
    }
  };

  const activeCount = strategies.filter((s) => s.is_active).length;

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Strategies</h1>
          <p className="text-sm text-slate-400">
            {strategies.length} total &middot; {activeCount} active
          </p>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-500"
        >
          {showForm ? <X className="h-4 w-4" /> : <Plus className="h-4 w-4" />}
          {showForm ? 'Cancel' : 'New Strategy'}
        </button>
      </div>

      {showForm && (
        <Card className="animate-fade-in">
          <CardHeader>
            <CardTitle className="text-base text-white">Create New Strategy</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label className="mb-1.5 block text-sm text-slate-400">Strategy Name</label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="e.g., Gold Scalper V2"
                  className="w-full rounded-lg border border-slate-700 bg-slate-800/50 px-3 py-2 text-sm text-white placeholder-slate-600 outline-none focus:border-blue-500"
                />
              </div>
              <div>
                <label className="mb-1.5 block text-sm text-slate-400">Strategy Type</label>
                <select
                  value={formData.type}
                  onChange={(e) => setFormData({ ...formData, type: e.target.value })}
                  className="w-full rounded-lg border border-slate-700 bg-slate-800/50 px-3 py-2 text-sm text-white outline-none focus:border-blue-500"
                >
                  <option value="scalping">Scalping</option>
                  <option value="day_trading">Day Trading</option>
                  <option value="swing">Swing Trading</option>
                  <option value="ict">ICT</option>
                  <option value="grid">Grid</option>
                </select>
              </div>
            </div>
            <button
              onClick={() => {
                setShowForm(false);
                setFormData({ name: '', type: 'scalping' });
              }}
              className="mt-4 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-emerald-500"
            >
              Create Strategy
            </button>
          </CardContent>
        </Card>
      )}

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {strategies.map((strategy) => (
          <Card
            key={strategy.id}
            className={cn(
              'cursor-pointer transition-all hover:border-slate-600/50',
              selected?.id === strategy.id && 'border-blue-500/50 ring-1 ring-blue-500/20'
            )}
            onClick={() => setSelected(selected?.id === strategy.id ? null : strategy)}
          >
            <CardContent className="p-5">
              <div className="mb-4 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  {strategy.type === 'scalping' ? (
                    <Zap className="h-5 w-5 text-amber-400" />
                  ) : (
                    <Bot className="h-5 w-5 text-blue-400" />
                  )}
                  <div>
                    <h3 className="font-semibold text-white">{strategy.name}</h3>
                    <p className="text-xs text-slate-500">{strategy.type}</p>
                  </div>
                </div>
                <Switch.Root
                  checked={strategy.is_active}
                  onCheckedChange={(checked) => handleToggle(strategy.id, checked)}
                  onClick={(e) => e.stopPropagation()}
                  className={cn(
                    'relative h-5 w-9 rounded-full transition-colors',
                    strategy.is_active ? 'bg-blue-500' : 'bg-slate-600'
                  )}
                >
                  <Switch.Thumb className="block h-4 w-4 translate-x-0.5 rounded-full bg-white transition-transform data-[state=checked]:translate-x-[18px]" />
                </Switch.Root>
              </div>

              <div className="grid grid-cols-3 gap-4">
                <div className="text-center">
                  <Target className="mx-auto mb-1 h-4 w-4 text-emerald-400" />
                  <p className="text-xs text-slate-500">Winrate</p>
                  <p className="text-sm font-semibold text-white">{formatPercent(strategy.winrate)}</p>
                </div>
                <div className="text-center">
                  <Shield className="mx-auto mb-1 h-4 w-4 text-blue-400" />
                  <p className="text-xs text-slate-500">PF</p>
                  <p className="text-sm font-semibold text-white">{formatNumber(strategy.profit_factor)}</p>
                </div>
                <div className="text-center">
                  <BarChart3 className="mx-auto mb-1 h-4 w-4 text-violet-400" />
                  <p className="text-xs text-slate-500">Trades</p>
                  <p className="text-sm font-semibold text-white">{strategy.total_trades}</p>
                </div>
              </div>

              <div className="mt-4">
                <div className="h-1.5 overflow-hidden rounded-full bg-slate-700">
                  <div
                    className={cn(
                      'h-full rounded-full transition-all',
                      strategy.winrate >= 0.6 ? 'bg-emerald-500' : strategy.winrate >= 0.4 ? 'bg-amber-500' : 'bg-red-500'
                    )}
                    style={{ width: `${strategy.winrate * 100}%` }}
                  />
                </div>
              </div>
            </CardContent>
          </Card>
        ))}

        {strategies.length === 0 && (
          <div className="col-span-full flex flex-col items-center justify-center rounded-xl border border-dashed border-slate-700 py-16 text-slate-500">
            <Bot className="mb-3 h-10 w-10" />
            <p>No strategies yet</p>
            <p className="text-xs">Create a strategy or ask JARVIS to build one</p>
          </div>
        )}
      </div>

      {selected && (
        <Card className="animate-fade-in">
          <CardHeader>
            <CardTitle className="text-base text-white">
              {selected.name} — Performance Details
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-6 sm:grid-cols-4">
              <div>
                <p className="text-xs text-slate-500">Type</p>
                <p className="mt-1 font-medium text-white">{selected.type}</p>
              </div>
              <div>
                <p className="text-xs text-slate-500">Status</p>
                <p className={cn('mt-1 font-medium', selected.is_active ? 'text-emerald-400' : 'text-slate-400')}>
                  {selected.is_active ? 'Active' : 'Inactive'}
                </p>
              </div>
              <div>
                <p className="text-xs text-slate-500">Winrate</p>
                <p className="mt-1 font-medium text-white">{formatPercent(selected.winrate)}</p>
              </div>
              <div>
                <p className="text-xs text-slate-500">Profit Factor</p>
                <p className="mt-1 font-medium text-white">{formatNumber(selected.profit_factor)}</p>
              </div>
              <div>
                <p className="text-xs text-slate-500">Total Trades</p>
                <p className="mt-1 font-medium text-white">{selected.total_trades}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
