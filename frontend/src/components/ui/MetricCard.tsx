export function MetricCard({ label, value, sub, color="text-brand-500" }: { label:string; value:string|number; sub?:string; color?:string }) {
  return (
    <div className="card p-5">
      <p className="text-[11px] font-semibold uppercase tracking-[0.08em] text-slate-500">{label}</p>
      <p className={`mt-2 text-2xl font-semibold tabular-nums tracking-tight ${color}`}>{value}</p>
      {sub && <p className="text-xs text-slate-400 mt-1">{sub}</p>}
    </div>
  );
}
