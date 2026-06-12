export const STATUS_CONFIG = {
  PENDING:                  { label: "Pendente",            badge: "bg-slate-100 text-slate-600",     step: 1 },
  IN_REVIEW:                { label: "Em análise",          badge: "bg-blue-100 text-blue-700",        step: 2 },
  APPROVED:                 { label: "Aprovado",            badge: "bg-emerald-100 text-emerald-700",  step: 3 },
  APPROVED_WITH_CONDITIONS: { label: "Aprovado c/ ressalvas", badge: "bg-amber-100 text-amber-700",   step: 3 },
  REJECTED:                 { label: "Rejeitado",           badge: "bg-red-100 text-red-700",          step: 3 },
  CANCELLED:                { label: "Cancelado",           badge: "bg-slate-100 text-slate-500",      step: 3 },
} as const;

export type StatusKey = keyof typeof STATUS_CONFIG;

export const OPERATION_TYPES = [
  "COMPRA", "VENDA", "SUBSCRIÇÃO", "RESGATE", "TRANSFERÊNCIA", "OUTRO",
] as const;