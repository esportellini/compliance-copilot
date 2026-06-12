export const DOCUMENT_TYPES = [
  { value: "INVESTMENT_POLICY",  label: "Política de investimentos pessoais" },
  { value: "ETHICS_CODE",        label: "Código de ética" },
  { value: "COMPLIANCE_MANUAL",  label: "Manual de compliance" },
  { value: "SUITABILITY_POLICY", label: "Política de suitability" },
  { value: "CONFLICT_POLICY",    label: "Política de conflitos de interesse" },
  { value: "RESTRICTED_LIST",    label: "Lista restrita" },
  { value: "WATCH_LIST",         label: "Lista de observação" },
  { value: "INTERNAL_MEMO",      label: "Comunicados internos" },
  { value: "OPERATIONAL_PROC",   label: "Procedimentos operacionais" },
  { value: "OTHER",              label: "Outro" },
] as const;

export const DOC_TYPE_MAP = Object.fromEntries(
  DOCUMENT_TYPES.map(({ value, label }) => [value, label])
) as Record<string, string>;

export const STATUS_OPTIONS = [
  { value: "DRAFT",    label: "Rascunho",  badge: "bg-slate-100 text-slate-600" },
  { value: "ACTIVE",   label: "Ativo",     badge: "bg-emerald-100 text-emerald-700" },
  { value: "ARCHIVED", label: "Arquivado", badge: "bg-amber-100 text-amber-700" },
] as const;

export const STATUS_MAP  = Object.fromEntries(STATUS_OPTIONS.map(({ value, label }) => [value, label])) as Record<string, string>;
export const STATUS_BADGE = Object.fromEntries(STATUS_OPTIONS.map(({ value, badge }) => [value, badge])) as Record<string, string>;

export function fmtSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 ** 2) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 ** 2).toFixed(1)} MB`;
}