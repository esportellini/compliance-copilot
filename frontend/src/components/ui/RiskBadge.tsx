import { Badge } from "./Badge";

const CONFIG: Record<string, { label: string; style: string; dot: string }> = {
  LOW: { label: "Baixo", style: "bg-emerald-50 text-emerald-800 ring-emerald-700/20", dot: "bg-emerald-600" },
  MEDIUM: { label: "Médio", style: "bg-amber-50 text-amber-900 ring-amber-700/20", dot: "bg-amber-600" },
  HIGH: { label: "Alto", style: "bg-red-50 text-red-800 ring-red-700/20", dot: "bg-red-600" },
};

export function RiskBadge({ risk }: { risk: string }) {
  const config = CONFIG[risk] ?? { label: risk, style: "bg-slate-100 text-slate-700 ring-slate-500/20", dot: "bg-slate-500" };
  return <Badge className={config.style}><span className={`h-1.5 w-1.5 rounded-full ${config.dot}`} aria-hidden="true" />Risco {config.label}</Badge>;
}
