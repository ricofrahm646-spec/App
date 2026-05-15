"use client";

import {
  Area,
  AreaChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

export function EquityChart({ data }: { data: { t: number; equity: number }[] }) {
  return (
    <div className="h-64 w-full">
      <ResponsiveContainer>
        <AreaChart data={data}>
          <defs>
            <linearGradient id="eq" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#22d3ee" stopOpacity={0.6} />
              <stop offset="100%" stopColor="#22d3ee" stopOpacity={0} />
            </linearGradient>
          </defs>
          <XAxis dataKey="t" hide />
          <YAxis stroke="#475569" fontSize={11} domain={["auto", "auto"]} />
          <Tooltip
            contentStyle={{ background: "#0f172a", border: "1px solid #1f2937" }}
            labelStyle={{ color: "#94a3b8" }}
          />
          <Area
            type="monotone"
            dataKey="equity"
            stroke="#22d3ee"
            strokeWidth={2}
            fill="url(#eq)"
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
