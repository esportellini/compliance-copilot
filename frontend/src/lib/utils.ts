import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export const DECISION_LABELS: Record<string, string> = {
  ALLOWED: "Permitido",
  REPORT_REQUIRED: "Requer Reporte",
  PRE_APPROVAL_REQUIRED: "Requer Pré-aprovação",
  RESTRICTED: "Restrito",
  INCONCLUSIVE: "Inconclusivo",
};

export const DECISION_COLORS: Record<string, string> = {
  ALLOWED: "bg-emerald-100 text-emerald-800",
  REPORT_REQUIRED: "bg-amber-100 text-amber-800",
  PRE_APPROVAL_REQUIRED: "bg-blue-100 text-blue-800",
  RESTRICTED: "bg-red-100 text-red-800",
  INCONCLUSIVE: "bg-slate-100 text-slate-700",
};

export const RISK_COLORS: Record<string, string> = {
  LOW: "bg-emerald-50 text-emerald-700",
  MEDIUM: "bg-amber-50 text-amber-700",
  HIGH: "bg-red-50 text-red-700",
};

export const ROLE_LABELS: Record<string, string> = {
  ADMIN: "Administrador",
  COMPLIANCE: "Compliance",
  EMPLOYEE: "Colaborador",
  AUDITOR: "Auditor",
};

export function fmtCurrency(v: number) {
  return new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(v);
}

export function fmtDate(d: string | Date) {
  return new Date(d).toLocaleDateString("pt-BR");
}

export function fmtDateTime(d: string | Date) {
  return new Date(d).toLocaleString("pt-BR");
}
