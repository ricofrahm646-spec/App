'use client';

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { api } from '@/lib/api';
import { Save, Loader2, MessageSquare, Monitor, ShieldCheck } from 'lucide-react';

interface FieldConfig {
  key: string;
  label: string;
  type: 'text' | 'number' | 'password';
  placeholder: string;
}

interface SectionConfig {
  id: string;
  title: string;
  icon: React.ReactNode;
  fields: FieldConfig[];
}

const SECTIONS: SectionConfig[] = [
  {
    id: 'telegram',
    title: 'Telegram Settings',
    icon: <MessageSquare className="h-4 w-4 text-blue-400" />,
    fields: [
      { key: 'bot_token', label: 'Bot Token', type: 'password', placeholder: 'Enter Telegram bot token' },
      { key: 'chat_id', label: 'Chat ID', type: 'text', placeholder: 'Enter Telegram chat ID' },
    ],
  },
  {
    id: 'mt5',
    title: 'MT5 Settings',
    icon: <Monitor className="h-4 w-4 text-emerald-400" />,
    fields: [
      { key: 'path', label: 'Terminal Path', type: 'text', placeholder: 'C:\\Program Files\\MT5\\terminal64.exe' },
      { key: 'login', label: 'Login', type: 'number', placeholder: 'MT5 account number' },
      { key: 'password', label: 'Password', type: 'password', placeholder: 'MT5 password' },
      { key: 'server', label: 'Server', type: 'text', placeholder: 'Broker server name' },
    ],
  },
  {
    id: 'risk',
    title: 'Risk Management',
    icon: <ShieldCheck className="h-4 w-4 text-amber-400" />,
    fields: [
      { key: 'max_risk_per_trade', label: 'Max Risk Per Trade (%)', type: 'number', placeholder: '2' },
      { key: 'max_daily_loss', label: 'Max Daily Loss (%)', type: 'number', placeholder: '5' },
      { key: 'max_drawdown', label: 'Max Drawdown (%)', type: 'number', placeholder: '10' },
    ],
  },
];

export default function SettingsPanel() {
  const [values, setValues] = useState<Record<string, Record<string, string>>>({});
  const [saving, setSaving] = useState<string | null>(null);
  const [saved, setSaved] = useState<string | null>(null);

  const updateField = (section: string, key: string, value: string) => {
    setValues((prev) => ({
      ...prev,
      [section]: { ...(prev[section] || {}), [key]: value },
    }));
  };

  const handleSave = async (sectionId: string) => {
    setSaving(sectionId);
    try {
      const data = values[sectionId] || {};
      const parsed: Record<string, unknown> = {};
      for (const [k, v] of Object.entries(data)) {
        parsed[k] = v;
      }
      await api.updateSettings(sectionId, parsed);
      setSaved(sectionId);
      setTimeout(() => setSaved(null), 2000);
    } catch {
      /* handle error */
    } finally {
      setSaving(null);
    }
  };

  return (
    <div className="space-y-6">
      {SECTIONS.map((section) => (
        <Card key={section.id}>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base text-white">
              {section.icon}
              {section.title}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {section.fields.map((field) => (
                <div key={field.key}>
                  <label className="mb-1.5 block text-sm text-slate-400">{field.label}</label>
                  <input
                    type={field.type}
                    placeholder={field.placeholder}
                    value={values[section.id]?.[field.key] || ''}
                    onChange={(e) => updateField(section.id, field.key, e.target.value)}
                    className="w-full rounded-lg border border-slate-700 bg-slate-800/50 px-3 py-2 text-sm text-white placeholder-slate-600 outline-none transition-colors focus:border-blue-500"
                  />
                </div>
              ))}
              <button
                onClick={() => handleSave(section.id)}
                disabled={saving === section.id}
                className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-500 disabled:opacity-50"
              >
                {saving === section.id ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Save className="h-4 w-4" />
                )}
                {saved === section.id ? 'Saved!' : 'Save'}
              </button>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
