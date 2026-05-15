import type { ModuleStatus as ModuleStatusType } from "@/lib/api";

const statusStyles: Record<ModuleStatusType["status"], string> = {
  healthy: "bg-emerald-500/15 text-emerald-300 ring-1 ring-emerald-500/30",
  degraded: "bg-amber-500/15 text-amber-300 ring-1 ring-amber-500/30",
  pending: "bg-slate-500/15 text-slate-300 ring-1 ring-slate-500/30",
};

export function ModuleStatus({ name, status, description }: ModuleStatusType) {
  return (
    <div className="flex items-start justify-between gap-4 rounded-2xl border border-white/10 bg-slate-950/70 p-4">
      <div>
        <h3 className="text-base font-semibold text-white">{name}</h3>
        <p className="mt-1 text-sm text-slate-300">{description}</p>
      </div>
      <span className={`rounded-full px-3 py-1 text-xs font-medium ${statusStyles[status]}`}>
        {status}
      </span>
    </div>
  );
}
