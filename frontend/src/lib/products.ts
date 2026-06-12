export const PRODUCT_TYPES = [
  { value: "STOCK",        label: "Ação" },
  { value: "FII",          label: "FII" },
  { value: "ETF",          label: "ETF" },
  { value: "OPEN_FUND",    label: "Fundo aberto" },
  { value: "CLOSED_FUND",  label: "Fundo fechado" },
  { value: "FIDC",         label: "FIDC" },
  { value: "FIXED_INCOME", label: "Renda fixa" },
  { value: "COE",          label: "COE" },
  { value: "DERIVATIVE",   label: "Derivativo" },
  { value: "CRYPTO",       label: "Criptoativo" },
  { value: "IPO",          label: "IPO / Oferta pública" },
  { value: "OTHER",        label: "Outro" },
] as const;

export const PRODUCT_TYPE_MAP = Object.fromEntries(
  PRODUCT_TYPES.map(({ value, label }) => [value, label])
) as Record<string, string>;

export const STATUS_OPTIONS = [
  { value: "ALLOWED",    label: "Permitido",   badge: "bg-emerald-100 text-emerald-700" },
  { value: "MONITORED",  label: "Monitorado",  badge: "bg-blue-100 text-blue-700" },
  { value: "RESTRICTED", label: "Restrito",    badge: "bg-amber-100 text-amber-700" },
  { value: "BLOCKED",    label: "Bloqueado",   badge: "bg-red-100 text-red-700" },
] as const;

export const STATUS_MAP = Object.fromEntries(
  STATUS_OPTIONS.map(({ value, label }) => [value, label])
) as Record<string, string>;

export const STATUS_BADGE = Object.fromEntries(
  STATUS_OPTIONS.map(({ value, badge }) => [value, badge])
) as Record<string, string>;

export const RISK_OPTIONS = [
  { value: "LOW",    label: "Baixo",  badge: "bg-emerald-50 text-emerald-700" },
  { value: "MEDIUM", label: "Médio",  badge: "bg-amber-50 text-amber-700" },
  { value: "HIGH",   label: "Alto",   badge: "bg-red-50 text-red-700" },
] as const;

export const RISK_MAP = Object.fromEntries(
  RISK_OPTIONS.map(({ value, label }) => [value, label])
) as Record<string, string>;

export const RISK_BADGE = Object.fromEntries(
  RISK_OPTIONS.map(({ value, badge }) => [value, badge])
) as Record<string, string>;

export const LIQUIDITY_OPTIONS = [
  "D+0", "D+1", "D+2", "D+3", "D+5", "D+30", "D+90", "D+180", "D+360", "Sem liquidez",
];