'use client';

import { useEffect, useState } from 'react';
import { Wifi, WifiOff, Brain, Clock } from 'lucide-react';
import { format } from 'date-fns';

interface StatusBarProps {
  mt5Connected?: boolean;
  activeStrategies?: number;
}

export default function StatusBar({ mt5Connected = false, activeStrategies = 0 }: StatusBarProps) {
  const [time, setTime] = useState(new Date());

  useEffect(() => {
    const interval = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="flex flex-wrap items-center gap-4 rounded-lg border border-slate-700/50 bg-slate-800/50 px-4 py-2 text-xs backdrop-blur-sm">
      <div className="flex items-center gap-2">
        {mt5Connected ? (
          <>
            <Wifi className="h-3.5 w-3.5 text-emerald-400" />
            <span className="text-emerald-400">MT5 Connected</span>
          </>
        ) : (
          <>
            <WifiOff className="h-3.5 w-3.5 text-red-400" />
            <span className="text-red-400">MT5 Disconnected</span>
          </>
        )}
      </div>

      <div className="h-3 w-px bg-slate-700" />

      <div className="flex items-center gap-2">
        <Brain className="h-3.5 w-3.5 text-blue-400" />
        <span className="text-blue-400">JARVIS AI Online</span>
      </div>

      <div className="h-3 w-px bg-slate-700" />

      <div className="flex items-center gap-2">
        <div className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
        <span className="text-slate-400">
          {activeStrategies} {activeStrategies === 1 ? 'Strategy' : 'Strategies'} Active
        </span>
      </div>

      <div className="ml-auto flex items-center gap-2 text-slate-400">
        <Clock className="h-3.5 w-3.5" />
        <span>{format(time, 'HH:mm:ss')}</span>
      </div>
    </div>
  );
}
