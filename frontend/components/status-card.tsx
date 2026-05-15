type StatusCardProps = {
  label: string;
  value: string;
  tone?: "neutral" | "positive" | "negative";
};

export function StatusCard({
  label,
  value,
  tone = "neutral"
}: StatusCardProps) {
  const valueClass =
    tone === "positive"
      ? "text-green-400"
      : tone === "negative"
        ? "text-red-400"
        : "text-white";

  return (
    <div className="panel p-5">
      <p className="text-sm uppercase tracking-[0.24em] text-slate-400">{label}</p>
      <p className={`mt-3 text-3xl font-semibold ${valueClass}`}>{value}</p>
    </div>
  );
}
