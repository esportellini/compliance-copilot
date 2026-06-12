import { Badge } from "./Badge";
import { DECISION_COLORS, DECISION_LABELS } from "@/lib/utils";
export function DecisionBadge({ decision }: { decision: string }) {
  return <Badge className={DECISION_COLORS[decision] ?? "bg-slate-100 text-slate-700"}>{DECISION_LABELS[decision] ?? decision}</Badge>;
}