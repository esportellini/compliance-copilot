export function PageHeader({ eyebrow, title, subtitle, action }: { eyebrow?: string; title: string; subtitle?: string; action?: React.ReactNode }) {
  return (
    <div className="mb-7 flex flex-col gap-4 border-b border-slate-200 pb-5 sm:flex-row sm:items-end sm:justify-between">
      <div className="max-w-3xl">
        {eyebrow && <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-[0.12em] text-brand-700">{eyebrow}</p>}
        <h1 className="text-2xl font-semibold tracking-[-0.025em] text-slate-950">{title}</h1>
        {subtitle && <p className="mt-1.5 text-sm leading-6 text-slate-500">{subtitle}</p>}
      </div>
      {action && <div className="shrink-0">{action}</div>}
    </div>
  );
}
