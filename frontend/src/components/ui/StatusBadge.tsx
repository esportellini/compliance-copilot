import { Badge } from "./Badge";
import { STATUS_CONFIG, type StatusKey } from "@/lib/pre-approvals";

const styles: Record<string, string> = {
  PENDING: "bg-slate-100 text-slate-700 ring-slate-500/20",
  IN_REVIEW: "bg-blue-50 text-blue-800 ring-blue-700/20",
  APPROVED: "bg-emerald-50 text-emerald-800 ring-emerald-700/20",
  APPROVED_WITH_CONDITIONS: "bg-amber-50 text-amber-900 ring-amber-700/20",
  REJECTED: "bg-red-50 text-red-800 ring-red-700/20",
  CANCELLED: "bg-slate-100 text-slate-500 ring-slate-400/20",
  ACTIVE: "bg-emerald-50 text-emerald-800 ring-emerald-700/20",
  DRAFT: "bg-slate-100 text-slate-700 ring-slate-500/20",
  ARCHIVED: "bg-slate-100 text-slate-500 ring-slate-400/20",
  RESTRICTED: "bg-red-50 text-red-800 ring-red-700/20",
  BLOCKED: "bg-red-50 text-red-800 ring-red-700/20",
  INACTIVE: "bg-slate-100 text-slate-500 ring-slate-400/20",
};

const genericLabels: Record<string, string> = { ACTIVE: "Ativo", DRAFT: "Rascunho", ARCHIVED: "Arquivado", RESTRICTED: "Restrito", BLOCKED: "Bloqueado", INACTIVE: "Inativo" };

export function StatusBadge({ status, label }: { status: string; label?: string }) {
  const stateLabel = label ?? STATUS_CONFIG[status as StatusKey]?.label ?? genericLabels[status] ?? status;
  return <Badge className={styles[status] ?? "bg-slate-100 text-slate-700 ring-slate-500/20"}><span className="h-1.5 w-1.5 rounded-full bg-current opacity-70" aria-hidden="true" />{stateLabel}</Badge>;
}
