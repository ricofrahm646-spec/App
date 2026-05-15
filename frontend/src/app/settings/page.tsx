'use client';

import { useState } from 'react';
import {
  Save,
  Server,
  Send,
  BarChart3,
  Shield,
  Brain,
  Eye,
  EyeOff,
  CheckCircle,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import type { Settings } from '@/types';

const mockSettings: Settings = {
  mt5: {
    server: 'MetaQuotes-Demo',
    login: '12345678',
    password: '••••••••',
    path: 'C:\\Program Files\\MetaTrader 5\\terminal64.exe',
  },
  telegram: {
    token: '1234567890:ABCdefGHIjklMNOpqrsTUVwxyz',
    chatId: '-1001234567890',
    enabled: true,
  },
  tradingview: {
    webhookUrl: 'http://localhost:8000/api/webhook/tradingview',
    secretKey: 'tv_secret_key_abc123',
    enabled: true,
  },
  risk: {
    maxRiskPerTrade: 2.0,
    maxDailyDrawdown: 5.0,
    maxOpenPositions: 5,
    defaultLotSize: 0.10,
  },
  ai: {
    modelType: 'LSTM',
    retrainInterval: 24,
    minConfidence: 0.70,
    features: ['price', 'volume', 'rsi', 'macd', 'atr', 'sentiment'],
  },
};

const tabs = [
  { id: 'mt5', label: 'MT5 Connection', icon: Server },
  { id: 'telegram', label: 'Telegram', icon: Send },
  { id: 'tradingview', label: 'TradingView', icon: BarChart3 },
  { id: 'risk', label: 'Risk Management', icon: Shield },
  { id: 'ai', label: 'AI Model', icon: Brain },
] as const;

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState<string>('mt5');
  const [settings, setSettings] = useState<Settings>(mockSettings);
  const [showPassword, setShowPassword] = useState(false);
  const [saved, setSaved] = useState(false);

  const handleSave = () => {
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const updateSetting = (section: keyof Settings, key: string, value: unknown) => {
    setSettings((prev) => ({
      ...prev,
      [section]: {
        ...(prev[section] as Record<string, unknown>),
        [key]: value,
      },
    }));
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-100">Settings</h1>
          <p className="mt-1 text-sm text-slate-500">
            Configure your trading system connections and parameters
          </p>
        </div>
        <button
          onClick={handleSave}
          className={cn(
            'flex items-center gap-2 rounded-xl px-5 py-2.5 text-sm font-medium text-white transition-all',
            saved ? 'bg-emerald-600' : 'bg-blue-600 hover:bg-blue-500'
          )}
        >
          {saved ? (
            <>
              <CheckCircle className="h-4 w-4" />
              Saved
            </>
          ) : (
            <>
              <Save className="h-4 w-4" />
              Save Changes
            </>
          )}
        </button>
      </div>

      <div className="flex gap-6">
        <div className="w-56 shrink-0 space-y-1">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={cn(
                  'flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors',
                  activeTab === tab.id
                    ? 'bg-slate-800 text-emerald-400'
                    : 'text-slate-400 hover:bg-slate-800/50 hover:text-slate-200'
                )}
              >
                <Icon className="h-4 w-4" />
                {tab.label}
              </button>
            );
          })}
        </div>

        <div className="flex-1 rounded-xl border border-slate-800 bg-slate-900/30 p-6">
          {activeTab === 'mt5' && (
            <div className="space-y-5">
              <h3 className="text-lg font-semibold text-slate-200">MT5 Connection Settings</h3>
              <p className="text-sm text-slate-500">Configure your MetaTrader 5 terminal connection.</p>
              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <label className="mb-1.5 block text-xs font-medium text-slate-500">Server</label>
                  <input
                    value={settings.mt5.server}
                    onChange={(e) => updateSetting('mt5', 'server', e.target.value)}
                    className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2.5 text-sm text-slate-200 outline-none focus:border-emerald-500/50"
                  />
                </div>
                <div>
                  <label className="mb-1.5 block text-xs font-medium text-slate-500">Login</label>
                  <input
                    value={settings.mt5.login}
                    onChange={(e) => updateSetting('mt5', 'login', e.target.value)}
                    className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2.5 text-sm text-slate-200 outline-none focus:border-emerald-500/50"
                  />
                </div>
                <div>
                  <label className="mb-1.5 block text-xs font-medium text-slate-500">Password</label>
                  <div className="relative">
                    <input
                      type={showPassword ? 'text' : 'password'}
                      value={settings.mt5.password}
                      onChange={(e) => updateSetting('mt5', 'password', e.target.value)}
                      className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2.5 pr-10 text-sm text-slate-200 outline-none focus:border-emerald-500/50"
                    />
                    <button
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
                    >
                      {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </button>
                  </div>
                </div>
                <div>
                  <label className="mb-1.5 block text-xs font-medium text-slate-500">Terminal Path</label>
                  <input
                    value={settings.mt5.path}
                    onChange={(e) => updateSetting('mt5', 'path', e.target.value)}
                    className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2.5 text-sm text-slate-200 outline-none focus:border-emerald-500/50"
                  />
                </div>
              </div>
            </div>
          )}

          {activeTab === 'telegram' && (
            <div className="space-y-5">
              <h3 className="text-lg font-semibold text-slate-200">Telegram Notifications</h3>
              <p className="text-sm text-slate-500">Configure Telegram bot for trade alerts and notifications.</p>
              <div className="flex items-center gap-3">
                <label className="text-sm font-medium text-slate-300">Enable Notifications</label>
                <button
                  onClick={() => updateSetting('telegram', 'enabled', !settings.telegram.enabled)}
                  className={cn(
                    'relative inline-flex h-6 w-11 items-center rounded-full transition-colors',
                    settings.telegram.enabled ? 'bg-emerald-600' : 'bg-slate-700'
                  )}
                >
                  <span className={cn(
                    'inline-block h-4 w-4 rounded-full bg-white transition-transform',
                    settings.telegram.enabled ? 'translate-x-6' : 'translate-x-1'
                  )} />
                </button>
              </div>
              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <label className="mb-1.5 block text-xs font-medium text-slate-500">Bot Token</label>
                  <input
                    value={settings.telegram.token}
                    onChange={(e) => updateSetting('telegram', 'token', e.target.value)}
                    className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2.5 text-sm text-slate-200 outline-none focus:border-emerald-500/50"
                  />
                </div>
                <div>
                  <label className="mb-1.5 block text-xs font-medium text-slate-500">Chat ID</label>
                  <input
                    value={settings.telegram.chatId}
                    onChange={(e) => updateSetting('telegram', 'chatId', e.target.value)}
                    className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2.5 text-sm text-slate-200 outline-none focus:border-emerald-500/50"
                  />
                </div>
              </div>
            </div>
          )}

          {activeTab === 'tradingview' && (
            <div className="space-y-5">
              <h3 className="text-lg font-semibold text-slate-200">TradingView Integration</h3>
              <p className="text-sm text-slate-500">Configure TradingView webhook for alert-based trading.</p>
              <div className="flex items-center gap-3">
                <label className="text-sm font-medium text-slate-300">Enable Webhook</label>
                <button
                  onClick={() => updateSetting('tradingview', 'enabled', !settings.tradingview.enabled)}
                  className={cn(
                    'relative inline-flex h-6 w-11 items-center rounded-full transition-colors',
                    settings.tradingview.enabled ? 'bg-emerald-600' : 'bg-slate-700'
                  )}
                >
                  <span className={cn(
                    'inline-block h-4 w-4 rounded-full bg-white transition-transform',
                    settings.tradingview.enabled ? 'translate-x-6' : 'translate-x-1'
                  )} />
                </button>
              </div>
              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <label className="mb-1.5 block text-xs font-medium text-slate-500">Webhook URL</label>
                  <input
                    value={settings.tradingview.webhookUrl}
                    onChange={(e) => updateSetting('tradingview', 'webhookUrl', e.target.value)}
                    className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2.5 text-sm text-slate-200 outline-none focus:border-emerald-500/50"
                  />
                </div>
                <div>
                  <label className="mb-1.5 block text-xs font-medium text-slate-500">Secret Key</label>
                  <input
                    value={settings.tradingview.secretKey}
                    onChange={(e) => updateSetting('tradingview', 'secretKey', e.target.value)}
                    className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2.5 text-sm text-slate-200 outline-none focus:border-emerald-500/50"
                  />
                </div>
              </div>
            </div>
          )}

          {activeTab === 'risk' && (
            <div className="space-y-5">
              <h3 className="text-lg font-semibold text-slate-200">Risk Management</h3>
              <p className="text-sm text-slate-500">Configure risk parameters for automated trading.</p>
              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <label className="mb-1.5 block text-xs font-medium text-slate-500">Max Risk Per Trade (%)</label>
                  <input
                    type="number"
                    value={settings.risk.maxRiskPerTrade}
                    onChange={(e) => updateSetting('risk', 'maxRiskPerTrade', parseFloat(e.target.value))}
                    step="0.1"
                    className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2.5 text-sm text-slate-200 outline-none focus:border-emerald-500/50"
                  />
                </div>
                <div>
                  <label className="mb-1.5 block text-xs font-medium text-slate-500">Max Daily Drawdown (%)</label>
                  <input
                    type="number"
                    value={settings.risk.maxDailyDrawdown}
                    onChange={(e) => updateSetting('risk', 'maxDailyDrawdown', parseFloat(e.target.value))}
                    step="0.5"
                    className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2.5 text-sm text-slate-200 outline-none focus:border-emerald-500/50"
                  />
                </div>
                <div>
                  <label className="mb-1.5 block text-xs font-medium text-slate-500">Max Open Positions</label>
                  <input
                    type="number"
                    value={settings.risk.maxOpenPositions}
                    onChange={(e) => updateSetting('risk', 'maxOpenPositions', parseInt(e.target.value))}
                    min="1"
                    className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2.5 text-sm text-slate-200 outline-none focus:border-emerald-500/50"
                  />
                </div>
                <div>
                  <label className="mb-1.5 block text-xs font-medium text-slate-500">Default Lot Size</label>
                  <input
                    type="number"
                    value={settings.risk.defaultLotSize}
                    onChange={(e) => updateSetting('risk', 'defaultLotSize', parseFloat(e.target.value))}
                    step="0.01"
                    min="0.01"
                    className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2.5 text-sm text-slate-200 outline-none focus:border-emerald-500/50"
                  />
                </div>
              </div>
            </div>
          )}

          {activeTab === 'ai' && (
            <div className="space-y-5">
              <h3 className="text-lg font-semibold text-slate-200">AI Model Settings</h3>
              <p className="text-sm text-slate-500">Configure AI model training and prediction parameters.</p>
              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <label className="mb-1.5 block text-xs font-medium text-slate-500">Model Type</label>
                  <select
                    value={settings.ai.modelType}
                    onChange={(e) => updateSetting('ai', 'modelType', e.target.value)}
                    className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2.5 text-sm text-slate-200 outline-none focus:border-emerald-500/50"
                  >
                    <option value="LSTM">LSTM</option>
                    <option value="GRU">GRU</option>
                    <option value="Transformer">Transformer</option>
                    <option value="XGBoost">XGBoost</option>
                    <option value="Ensemble">Ensemble</option>
                  </select>
                </div>
                <div>
                  <label className="mb-1.5 block text-xs font-medium text-slate-500">Retrain Interval (hours)</label>
                  <input
                    type="number"
                    value={settings.ai.retrainInterval}
                    onChange={(e) => updateSetting('ai', 'retrainInterval', parseInt(e.target.value))}
                    min="1"
                    className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2.5 text-sm text-slate-200 outline-none focus:border-emerald-500/50"
                  />
                </div>
                <div>
                  <label className="mb-1.5 block text-xs font-medium text-slate-500">Min Confidence Threshold</label>
                  <input
                    type="number"
                    value={settings.ai.minConfidence}
                    onChange={(e) => updateSetting('ai', 'minConfidence', parseFloat(e.target.value))}
                    step="0.05"
                    min="0"
                    max="1"
                    className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2.5 text-sm text-slate-200 outline-none focus:border-emerald-500/50"
                  />
                </div>
                <div>
                  <label className="mb-1.5 block text-xs font-medium text-slate-500">Features</label>
                  <div className="flex flex-wrap gap-2">
                    {settings.ai.features.map((feature) => (
                      <span
                        key={feature}
                        className="rounded-full bg-slate-800 px-2.5 py-1 text-xs font-medium text-slate-300"
                      >
                        {feature}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
