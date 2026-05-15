import clsx from "clsx";

export function Stat({
  label,
  value,
  tone = "neutral",
  unit,
}: {
  label: string;
  value: string | number;
  unit?: string;
  tone?: "neutral" | "good" | "bad" | "warn";
}) {
  const toneClass = {
    neutral: "text-slate-100",
    good: "text-jarvis-ok",
    bad: "text-jarvis-err",
    warn: "text-jarvis-warn",
  }[tone];

  return (
    <div className="flex flex-col">
      <span className="text-xs uppercase tracking-widest text-slate-500">
        {label}
      </span>
      <span className={clsx("text-2xl font-semibold font-mono", toneClass)}>
        {value}
        {unit && <span className="ml-1 text-sm text-slate-400">{unit}</span>}
      </span>
    </div>
  );
}
