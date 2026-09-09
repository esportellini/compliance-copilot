const LABELS: Record<string, string> = { ON_TIME: "No prazo", DUE_SOON: "Vence em breve", OVERDUE: "Vencida", COMPLETED: "Concluída" };
const TONES: Record<string, string> = { ON_TIME: "bg-emerald-50 text-emerald-700", DUE_SOON: "bg-amber-50 text-amber-800", OVERDUE: "bg-red-50 text-red-700", COMPLETED: "bg-slate-100 text-slate-600" };

export function SlaBadge({ status }: { status: string }) {
  return <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-semibold ${TONES[status] ?? TONES.ON_TIME}`}>{LABELS[status] ?? status}</span>;
}
