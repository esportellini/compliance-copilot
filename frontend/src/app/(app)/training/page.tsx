"use client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { PageHeader } from "@/components/layout/PageHeader";
import { Alert } from "@/components/ui/Alert";
import { Spinner } from "@/components/ui/Spinner";
import { CheckCircle2, Circle, BookOpen, AlertTriangle } from "lucide-react";

const CATEGORY_CONFIG: Record<string, { label: string; color: string }> = {
  TOOL:       { label: "Uso do Copilot",   color: "bg-blue-50 text-blue-800 ring-1 ring-blue-700/20" },
  COMPLIANCE: { label: "Compliance",       color: "bg-brand-50 text-brand-800 ring-1 ring-brand-700/20" },
  PRIVACIDADE:{ label: "Privacidade",      color: "bg-emerald-50 text-emerald-800 ring-1 ring-emerald-700/20" },
  ETICA:      { label: "Ética",            color: "bg-amber-50 text-amber-900 ring-1 ring-amber-700/20" },
  POLICY:     { label: "Política",         color: "bg-slate-100 text-slate-600" },
  OPERATIONS: { label: "Operações",        color: "bg-slate-100 text-slate-700 ring-1 ring-slate-500/20" },
};

const TERMS = [
  "Li o termo de uso do Compliance Copilot.",
  "Entendi que a IA não substitui a análise humana de compliance.",
  "Entendi que devo inserir apenas dados necessários para a consulta.",
  "Entendi que todas as consultas podem ser auditadas pela equipe de compliance.",
  "Entendi o fluxo de pré-aprovação e quando utilizá-lo.",
];

export default function TrainingPage() {
  const qc = useQueryClient();
  const { user } = useAuth();
  const canAcknowledge = !!user && ["ADMIN", "EMPLOYEE"].includes(user.role);
  const [acceptedTerms, setAcceptedTerms] = useState<Set<number>>(new Set());
  const [termsSaved, setTermsSaved] = useState(false);

  const { data: progress } = useQuery({
    queryKey: ["training-progress"],
    queryFn: () => api.get("/training/progress").then(r => r.data),
  });

  const { data = [], isLoading } = useQuery({
    queryKey: ["training"],
    queryFn: () => api.get("/training").then(r => r.data),
  });

  const ack = useMutation({
    mutationFn: (id: number) => api.post("/training/acknowledge", { training_item_id: id }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["training"] });
      qc.invalidateQueries({ queryKey: ["training-progress"] });
    },
  });

  const total = progress?.total ?? 0;
  const done = progress?.completed ?? 0;
  const pct = progress?.percent ?? 0;
  const allRequiredDone = progress?.all_required_done ?? false;

  const grouped: Record<string, any[]> = {};
  for (const item of data) {
    const cat = item.category ?? "OTHER";
    if (!grouped[cat]) grouped[cat] = [];
    grouped[cat].push(item);
  }

  const toggleTerm = (i: number) => {
    setAcceptedTerms(prev => {
      const next = new Set(prev);
      next.has(i) ? next.delete(i) : next.add(i);
      return next;
    });
  };

  return (
    <div className="max-w-5xl space-y-6">
      <PageHeader title="Treinamentos" subtitle={`${done} de ${total} concluídos`} />

      {/* barra de progresso */}
      <div className="card p-5">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-slate-700">Progresso geral</span>
          <span className="text-sm font-bold text-brand-600">{pct}%</span>
        </div>
          <div className="h-2 w-full rounded-full bg-slate-100" role="progressbar" aria-label="Progresso dos treinamentos" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100}>
          <div
            className="bg-brand-500 h-2.5 rounded-full transition-all"
            style={{ width: `${pct}%` }}
          />
        </div>
        {allRequiredDone ? (
          <p className="text-xs text-emerald-600 mt-2 flex items-center gap-1">
            <CheckCircle2 size={13} /> Todos os itens obrigatórios concluídos
          </p>
        ) : (
          <p className="text-xs text-amber-600 mt-2 flex items-center gap-1">
            <AlertTriangle size={13} /> {(progress?.required ?? 0) - (progress?.completed_required ?? 0)} item(ns) obrigatório(s) pendente(s)
          </p>
        )}
      </div>

      {/* conteúdos por categoria */}
      {isLoading ? (
        <div className="flex justify-center py-16"><Spinner className="h-8 w-8" /></div>
      ) : (
        Object.entries(grouped).map(([cat, items]) => {
          const cfg = CATEGORY_CONFIG[cat] ?? { label: cat, color: "bg-slate-100 text-slate-600" };
          return (
            <div key={cat}>
              <div className="flex items-center gap-2 mb-3">
                <BookOpen size={14} className="text-slate-400" />
                <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${cfg.color}`}>
                  {cfg.label}
                </span>
              </div>
              <div className="grid gap-3 lg:grid-cols-2">
                {items.map((item: any) => (
                  <div key={item.id}
                    className={`card p-5 transition-colors ${item.acknowledged ? "border-emerald-200 bg-emerald-50/30" : ""}`}>
                    <div className="flex items-start gap-4">
                      <button
                        onClick={() => canAcknowledge && !item.acknowledged && ack.mutate(item.id)}
                        disabled={item.acknowledged || !canAcknowledge}
                        className="shrink-0 mt-0.5" aria-label={item.acknowledged ? `${item.title}: concluído` : `Marcar ${item.title} como lido`}>
                        {item.acknowledged
                          ? <CheckCircle2 size={20} className="text-emerald-500" />
                          : <Circle size={20} className="text-slate-300 hover:text-brand-400 transition-colors" />}
                      </button>
                      <div className="flex-1">
                        <div className="flex items-start justify-between gap-2 mb-1">
                          <p className={`font-medium text-sm ${item.acknowledged ? "text-slate-500" : "text-slate-800"}`}>
                            {item.title}
                          </p>
                          {item.required && !item.acknowledged && (
                            <span className="text-xs bg-amber-100 text-amber-700 px-1.5 py-0.5 rounded shrink-0">
                              obrigatório
                            </span>
                          )}
                        </div>
                        <p className="text-sm text-slate-500 leading-relaxed">{item.body}</p>
                        {canAcknowledge && !item.acknowledged && (
                          <button
                            onClick={() => ack.mutate(item.id)}
                            className="mt-3 text-xs text-brand-600 hover:text-brand-700 font-medium">
                            Marcar como lido →
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          );
        })
      )}

      {/* checklist de termos */}
      <div className="card p-5">
        <h2 className="text-sm font-semibold text-slate-800 mb-4 flex items-center gap-2">
          <AlertTriangle size={15} className="text-amber-500" />
          Checklist de aceite de uso
        </h2>
        <div className="space-y-3 mb-4">
          {TERMS.map((term, i) => (
            <label key={i} className="flex items-start gap-3 cursor-pointer group">
              <input
                type="checkbox"
                checked={acceptedTerms.has(i)}
                onChange={() => toggleTerm(i)}
                disabled={!canAcknowledge}
                className="mt-0.5 rounded border-slate-300"
              />
              <span className="text-sm text-slate-700 group-hover:text-slate-900">{term}</span>
            </label>
          ))}
        </div>
        {!canAcknowledge ? (
          <Alert variant="info" className="text-sm">Visualização somente leitura para Auditor.</Alert>
        ) : termsSaved ? (
          <Alert variant="success" className="text-sm">
            Termos registrados. Obrigado por confirmar o uso responsável do Copilot.
          </Alert>
        ) : (
          <button
            disabled={acceptedTerms.size < TERMS.length}
            onClick={() => setTermsSaved(true)}
            className="btn-primary text-sm disabled:opacity-40">
            Confirmar aceite ({acceptedTerms.size}/{TERMS.length})
          </button>
        )}
      </div>
    </div>
  );
}
