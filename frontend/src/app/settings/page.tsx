'use client';

import SettingsPanel from '@/components/settings/SettingsPanel';

export default function SettingsPage() {
  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h1 className="text-2xl font-bold text-white">Settings</h1>
        <p className="text-sm text-slate-400">Configure JARVIS trading system</p>
      </div>
      <div className="max-w-2xl">
        <SettingsPanel />
      </div>
    </div>
  );
}
