import clsx from "clsx";

export function Card({
  title,
  children,
  className,
}: {
  title?: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={clsx(
        "rounded-2xl border border-jarvis-border bg-jarvis-surface p-4 shadow-lg",
        className,
      )}
    >
      {title && (
        <h3 className="mb-3 text-xs font-semibold uppercase tracking-widest text-slate-400">
          {title}
        </h3>
      )}
      {children}
    </div>
  );
}
