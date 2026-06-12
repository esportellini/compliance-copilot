import { Badge } from "./Badge";
import { RISK_COLORS } from "@/lib/utils";
const LABELS: Record<string,string> = { LOW:"Baixo", MEDIUM:"Médio", HIGH:"Alto" };
export function RiskBadge({ risk }: { risk: string }) {
  return <Badge className={RISK_COLORS[risk] ?? "bg-slate-100 text-slate-700"}>{LABELS[risk] ?? risk}</Badge>;
}