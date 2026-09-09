import { VersionBadge } from "./VersionBadge";

export function ProvenancePanel({ rules }: { rules: any[] }) {
  if (!rules?.length) return null;
  return <section className="card mb-4 overflow-hidden"><div className="border-b border-slate-100 px-5 py-3"><h3 className="text-sm font-semibold text-slate-800">Proveniência da decisão</h3><p className="mt-1 text-xs text-slate-500">Snapshot das versões vigentes no instante da análise.</p></div><div className="divide-y divide-slate-100">{rules.map(rule => <div key={`${rule.rule_key}-${rule.version}`} className="flex flex-wrap items-center gap-3 px-5 py-4"><div className="min-w-0 flex-1"><p className="text-sm font-semibold text-slate-900">{rule.name}</p><p className="mt-1 font-mono text-xs text-slate-500">{rule.rule_key} · prioridade {rule.priority}</p></div><VersionBadge version={rule.version} status="ACTIVE" /><span className="font-mono text-xs text-slate-500">{rule.decision}</span></div>)}</div></section>;
}
