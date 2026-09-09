export function VersionBadge({ version, status }: { version: number; status: string }) {
  const tone = status === "ACTIVE" ? "bg-emerald-50 text-emerald-700" : status === "DRAFT" ? "bg-blue-50 text-blue-700" : "bg-slate-100 text-slate-500";
  return <span className={`inline-flex rounded-full px-2 py-0.5 font-mono text-[11px] font-semibold ${tone}`}>v{version} · {status}</span>;
}
