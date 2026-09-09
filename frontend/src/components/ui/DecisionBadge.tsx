import { Ban, CheckCircle2, CircleHelp, ClipboardList, ShieldQuestion } from "lucide-react";
import { Badge } from "./Badge";
import { DECISION_LABELS } from "@/lib/utils";

const CONFIG: Record<string, { style: string; icon: typeof CheckCircle2 }> = {
  ALLOWED: { style: "bg-emerald-50 text-emerald-800 ring-emerald-700/20", icon: CheckCircle2 },
  REPORT_REQUIRED: { style: "bg-blue-50 text-blue-800 ring-blue-700/20", icon: ClipboardList },
  PRE_APPROVAL_REQUIRED: { style: "bg-amber-50 text-amber-900 ring-amber-700/25", icon: ShieldQuestion },
  RESTRICTED: { style: "bg-red-50 text-red-800 ring-red-700/20", icon: Ban },
  INCONCLUSIVE: { style: "bg-slate-100 text-slate-700 ring-slate-500/20", icon: CircleHelp },
};

export function DecisionBadge({ decision }: { decision: string }) {
  const config = CONFIG[decision] ?? CONFIG.INCONCLUSIVE;
  const Icon = config.icon;
  return <Badge className={config.style}><Icon size={13} strokeWidth={2} aria-hidden="true" />{DECISION_LABELS[decision] ?? decision}</Badge>;
}
