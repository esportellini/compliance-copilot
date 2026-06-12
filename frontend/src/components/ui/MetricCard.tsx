export function MetricCard({ label, value, sub, color="text-brand-500" }: { label:string; value:string|number; sub?:string; color?:string }) {
  return (
    <div className="card p-5">
      <p className="text-xs text-slate-500 uppercase tracking-wide mb-1">{label}</p>
      <p className={`text-3xl font-bold ${color}`}>{value}</p>
      {sub && <p className="text-xs text-slate-400 mt-1">{sub}</p>}
    </div>
  );
}