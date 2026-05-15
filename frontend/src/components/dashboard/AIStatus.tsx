'use client';

import { Brain, Zap, Target, Clock, Activity } from 'lucide-react';
import { cn, statusColor, statusDotColor, formatPercentage } from '@/lib/utils';
import type { AIModelStatus } from '@/types';

const mockAIStatus: AIModelStatus = {
  modelName: 'JARVIS-LSTM-v3',
  status: 'trained',
  activeStrategy: 'AI Scalper Pro',
  lastPrediction: {
    symbol: 'EURUSD',
    direction: 'BUY',
    confidence: 0.847,
    timestamp: new Date(Date.now() - 120000).toISOString(),
  },
  accuracy: 72.4,
  trainingProgress: 100,
  lastTrainedAt: new Date(Date.now() - 3600000).toISOString(),
};

export function AIStatus() {
  const ai = mockAIStatus;

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/30 p-5">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-400">
          AI System Status
        </h3>
        <div className="flex items-center gap-2">
          <div className={cn('h-2 w-2 rounded-full pulse-dot', statusDotColor(ai.status))} />
          <span className={cn('text-xs font-medium capitalize', statusColor(ai.status))}>
            {ai.status}
          </span>
        </div>
      </div>

      <div className="space-y-4">
        <div className="flex items-center gap-3 rounded-lg bg-slate-800/30 p-3">
          <div className="rounded-lg bg-purple-500/20 p-2">
            <Brain className="h-5 w-5 text-purple-400" />
          </div>
          <div>
            <p className="text-sm font-semibold text-slate-200">{ai.modelName}</p>
            <p className="text-xs text-slate-500">Active Strategy: {ai.activeStrategy}</p>
          </div>
        </div>

        {ai.lastPrediction && (
          <div className="rounded-lg border border-slate-800 p-3">
            <p className="mb-2 text-xs font-medium uppercase tracking-wider text-slate-500">
              Last Prediction
            </p>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Zap className="h-4 w-4 text-amber-400" />
                <span className="font-semibold text-slate-200">
                  {ai.lastPrediction.symbol}
                </span>
                <span
                  className={cn(
                    'rounded px-1.5 py-0.5 text-xs font-bold',
                    ai.lastPrediction.direction === 'BUY'
                      ? 'bg-emerald-500/10 text-emerald-400'
                      : ai.lastPrediction.direction === 'SELL'
                      ? 'bg-red-500/10 text-red-400'
                      : 'bg-slate-500/10 text-slate-400'
                  )}
                >
                  {ai.lastPrediction.direction}
                </span>
              </div>
            </div>
            <div className="mt-2 flex items-center gap-4">
              <div className="flex items-center gap-1">
                <Target className="h-3 w-3 text-emerald-400" />
                <span className="text-xs text-slate-400">
                  Confidence:{' '}
                  <span className="font-semibold text-emerald-400">
                    {(ai.lastPrediction.confidence * 100).toFixed(1)}%
                  </span>
                </span>
              </div>
              <div className="flex items-center gap-1">
                <Clock className="h-3 w-3 text-slate-500" />
                <span className="text-xs text-slate-500">
                  {new Date(ai.lastPrediction.timestamp).toLocaleTimeString()}
                </span>
              </div>
            </div>
          </div>
        )}

        <div className="grid grid-cols-2 gap-3">
          <div className="rounded-lg bg-slate-800/30 p-3 text-center">
            <p className="text-xs text-slate-500">Accuracy</p>
            <p className="mt-1 text-lg font-bold text-emerald-400">{ai.accuracy}%</p>
          </div>
          <div className="rounded-lg bg-slate-800/30 p-3 text-center">
            <p className="text-xs text-slate-500">Training</p>
            <p className="mt-1 text-lg font-bold text-blue-400">{ai.trainingProgress}%</p>
          </div>
        </div>
      </div>
    </div>
  );
}
