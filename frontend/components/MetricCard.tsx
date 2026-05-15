type MetricCardProps = {
  label: string;
  value: string | number;
  tone?: "neutral" | "success" | "danger";
};

const toneClass = {
  neutral: "border-slate-700 text-slate-100",
  success: "border-emerald-500/50 text-emerald-300",
  danger: "border-red-500/50 text-red-300"
};

export function MetricCard({ label, value, tone = "neutral" }: MetricCardProps) {
  return (
    <div className={`rounded-2xl border bg-slate-900/70 p-4 shadow-xl ${toneClass[tone]}`}>
      <p className="text-xs uppercase tracking-[0.25em] text-slate-400">{label}</p>
      <p className="mt-3 text-2xl font-semibold">{value}</p>
    </div>
  );
}
