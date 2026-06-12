export const DECISION_CONFIG = {
  ALLOWED: {
    label:      "Permitido",
    badge:      "bg-emerald-100 text-emerald-800",
    border:     "border-emerald-200",
    bg:         "bg-emerald-50",
    icon:       "✅",
  },
  REPORT_REQUIRED: {
    label:      "Requer Reporte",
    badge:      "bg-amber-100 text-amber-800",
    border:     "border-amber-200",
    bg:         "bg-amber-50",
    icon:       "📋",
  },
  PRE_APPROVAL_REQUIRED: {
    label:      "Requer Pré-aprovação",
    badge:      "bg-blue-100 text-blue-800",
    border:     "border-blue-200",
    bg:         "bg-blue-50",
    icon:       "🔐",
  },
  RESTRICTED: {
    label:      "Restrito",
    badge:      "bg-red-100 text-red-800",
    border:     "border-red-200",
    bg:         "bg-red-50",
    icon:       "🚫",
  },
  INCONCLUSIVE: {
    label:      "Inconclusivo",
    badge:      "bg-slate-100 text-slate-700",
    border:     "border-slate-200",
    bg:         "bg-slate-50",
    icon:       "❓",
  },
} as const;

export type DecisionKey = keyof typeof DECISION_CONFIG;

export const RISK_CONFIG = {
  LOW:    { label: "Baixo",  badge: "bg-emerald-50 text-emerald-700" },
  MEDIUM: { label: "Médio",  badge: "bg-amber-50 text-amber-700" },
  HIGH:   { label: "Alto",   badge: "bg-red-50 text-red-700" },
} as const;

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
  { value: "IPO",          label: "IPO" },
  { value: "OTHER",        label: "Outro" },
] as const;

export const SUGGESTED_QUESTIONS = [
  "Posso investir em um fundo de renda fixa com R$ 50.000?",
  "Preciso de pré-aprovação para comprar ações da XPTO3?",
  "Criptoativos são permitidos para colaboradores?",
  "Como reportar uma aplicação em fundo aberto acima de R$ 100 mil?",
  "Fundos fechados exigem análise especial?",
  "Qual o prazo para registrar operações no sistema de controles?",
];