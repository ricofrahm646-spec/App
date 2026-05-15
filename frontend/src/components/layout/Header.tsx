'use client';

import { useState } from 'react';
import {
  Bell,
  Wifi,
  WifiOff,
  Database,
  Server,
  RefreshCw,
  X,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import type { Notification } from '@/types';

const mockNotifications: Notification[] = [
  {
    id: '1',
    type: 'trade',
    title: 'Trade Executed',
    message: 'BUY EURUSD 0.10 lots @ 1.0876',
    timestamp: new Date(Date.now() - 300000).toISOString(),
    read: false,
  },
  {
    id: '2',
    type: 'success',
    title: 'Strategy Update',
    message: 'AI Scalper strategy activated',
    timestamp: new Date(Date.now() - 900000).toISOString(),
    read: false,
  },
  {
    id: '3',
    type: 'warning',
    title: 'Risk Alert',
    message: 'Daily drawdown approaching 3% limit',
    timestamp: new Date(Date.now() - 1800000).toISOString(),
    read: true,
  },
];

interface ConnectionBadgeProps {
  label: string;
  connected: boolean;
  icon: React.ReactNode;
}

function ConnectionBadge({ label, connected, icon }: ConnectionBadgeProps) {
  return (
    <div
      className={cn(
        'flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium transition-colors',
        connected
          ? 'bg-emerald-500/10 text-emerald-400'
          : 'bg-red-500/10 text-red-400'
      )}
    >
      {icon}
      <span>{label}</span>
      <div
        className={cn(
          'h-1.5 w-1.5 rounded-full',
          connected ? 'bg-emerald-400 pulse-dot' : 'bg-red-400'
        )}
      />
    </div>
  );
}

export function Header() {
  const [showNotifications, setShowNotifications] = useState(false);
  const [notifications, setNotifications] = useState(mockNotifications);
  const unreadCount = notifications.filter((n) => !n.read).length;

  const markAllRead = () => {
    setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
  };

  return (
    <header className="flex items-center justify-between border-b border-slate-800 bg-slate-950/80 px-6 py-3 backdrop-blur-sm">
      <div className="flex items-center gap-3">
        <ConnectionBadge
          label="MT5"
          connected={true}
          icon={<Server className="h-3 w-3" />}
        />
        <ConnectionBadge
          label="Redis"
          connected={true}
          icon={<Database className="h-3 w-3" />}
        />
        <ConnectionBadge
          label="DB"
          connected={true}
          icon={<Database className="h-3 w-3" />}
        />
      </div>

      <div className="flex items-center gap-4">
        <button className="flex items-center gap-2 rounded-lg bg-slate-800 px-3 py-1.5 text-xs font-medium text-slate-300 transition-colors hover:bg-slate-700">
          <RefreshCw className="h-3 w-3" />
          Sync
        </button>

        <div className="relative">
          <button
            onClick={() => setShowNotifications(!showNotifications)}
            className="relative rounded-lg p-2 text-slate-400 transition-colors hover:bg-slate-800 hover:text-slate-200"
          >
            <Bell className="h-5 w-5" />
            {unreadCount > 0 && (
              <span className="absolute -right-0.5 -top-0.5 flex h-4 w-4 items-center justify-center rounded-full bg-emerald-500 text-[10px] font-bold text-white">
                {unreadCount}
              </span>
            )}
          </button>

          {showNotifications && (
            <div className="fade-in absolute right-0 top-full z-50 mt-2 w-80 rounded-xl border border-slate-700 bg-slate-900 shadow-2xl">
              <div className="flex items-center justify-between border-b border-slate-800 p-3">
                <h3 className="text-sm font-semibold text-slate-200">
                  Notifications
                </h3>
                <button
                  onClick={markAllRead}
                  className="text-xs text-slate-500 hover:text-slate-300"
                >
                  Mark all read
                </button>
              </div>
              <div className="max-h-80 overflow-y-auto">
                {notifications.map((notif) => (
                  <div
                    key={notif.id}
                    className={cn(
                      'border-b border-slate-800/50 px-4 py-3 transition-colors hover:bg-slate-800/30',
                      !notif.read && 'bg-slate-800/20'
                    )}
                  >
                    <div className="flex items-start justify-between">
                      <div>
                        <p className="text-sm font-medium text-slate-200">
                          {notif.title}
                        </p>
                        <p className="mt-0.5 text-xs text-slate-400">
                          {notif.message}
                        </p>
                      </div>
                      {!notif.read && (
                        <div className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-emerald-400" />
                      )}
                    </div>
                    <p className="mt-1 text-[10px] text-slate-600">
                      {new Date(notif.timestamp).toLocaleTimeString()}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="flex items-center gap-2 rounded-lg bg-slate-800/50 px-3 py-1.5">
          <Wifi className="h-3.5 w-3.5 text-emerald-400" />
          <span className="text-xs font-medium text-slate-300">Live</span>
        </div>
      </div>
    </header>
  );
}
