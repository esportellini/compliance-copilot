"use client";
import { useQuery } from "@tanstack/react-query";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";
import { PageHeader } from "@/components/layout/PageHeader";
import { Alert } from "@/components/ui/Alert";
import { Spinner } from "@/components/ui/Spinner";
import { DecisionBadge } from "@/components/ui/DecisionBadge";
import { RiskBadge } from "@/components/ui/RiskBadge";
import { SourceCard } from "@/components/ui/SourceCard";
import { ProvenancePanel } from "@/components/ui/ProvenancePanel";
import { DECISION_CONFIG, type DecisionKey } from "@/lib/copilot";
import { fmtCurrency, fmtDateTime } from "@/lib/utils";
import { ChevronLeft, AlertTriangle, ClipboardCheck } from "lucide-react";

function DetailRow({ label, value }: { label: string; value?: string | number | null }) {
  if (value === null || value === undefined || value === "") return null;
  return (
    <div className="flex gap-2">
      <span className="w-36 shrink-0 text-xs text-slate-500 pt-0.5">{label}</span>
      <span className="text-sm text-slate-800">{String(value)}</span>
    </div>
  );
}

export default function HistoryDetailPage() {
  const { id } = useParams<{ id: string }>();

  const { data, isLoading, error } = useQuery({
    queryKey: ["history-detail", id],
    queryFn: () => api.get(`/copilot/history/${id}`).then((r) => r.data),
  });

  if (isLoading) return <div className="flex justify-center py-20"><Spinner className="h-8 w-8" /></div>;
  if (error || !data) return (
    <Alert variant="error">
      {(error as any)?.response?.data?.detail ?? "Não foi possível carregar a consulta."}
    </Alert>
  );

  const ans = data.answer;
  const decision = ans.decision as DecisionKey;
  const dcfg = DECISION_CONFIG[decision] ?? DECISION_CONFIG.INCONCLUSIVE;

  return (
    <div className="max-w-5xl">
      <div className="flex items-center gap-2 text-sm text-slate-500 mb-4">
        <Link href="/history" className="hover:text-brand-600 flex items-center gap-1">
          <ChevronLeft size={14} /> Histórico
        </Link>
        <span>/</span>
        <span className="text-slate-700 truncate max-w-xs">{data.question}</span>
      </div>

      <PageHeader title="Detalhe da consulta" subtitle={fmtDateTime(data.created_at)} />

      {/* pergunta */}
      <div className="card p-5 mb-4">
        <p className="text-xs text-slate-500 mb-1">Pergunta</p>
        <p className="text-sm text-slate-800 font-medium">{data.question}</p>
        {(data.product_label || data.product_identifier || data.product_type || data.amount || data.objective) && (
          <div className="mt-3 space-y-1.5 pt-3 border-t border-slate-100">
            <DetailRow label="Produto" value={data.product_label} />
            <DetailRow label="Ticker/identificador" value={data.product_identifier} />
            <DetailRow label="Tipo de produto" value={data.product_type} />
            <DetailRow label="Valor" value={data.amount ? fmtCurrency(data.amount) : null} />
            <DetailRow label="Objetivo" value={data.objective} />
          </div>
        )}
      </div>

      {/* decisão */}
      <div className={`card border-2 ${dcfg.border} overflow-hidden mb-4`}>
        <div className={`${dcfg.bg} px-5 py-3 border-b ${dcfg.border} flex items-center gap-3 flex-wrap`}>
          <DecisionBadge decision={decision} />
          <RiskBadge risk={ans.risk_level} />
          {ans.requires_human_review && (
            <span className="flex items-center gap-1 text-xs font-medium bg-amber-100 text-amber-700 px-2 py-0.5 rounded-full">
              <AlertTriangle size={11} /> Revisão humana
            </span>
          )}
          <span className="text-xs text-slate-400 ml-auto">
            Confiança {Math.round(ans.confidence * 100)}%
          </span>
        </div>

        <div className="px-5 py-4 space-y-4">
          {ans.next_action && (
            <Alert variant={decision === "RESTRICTED" ? "error" : decision === "ALLOWED" ? "success" : "info"}>
              <span className="font-semibold">Próximo passo: </span>{ans.next_action}
            </Alert>
          )}

          <div>
            <p className="text-xs text-slate-500 mb-1">Justificativa</p>
            <p className="text-sm text-slate-700 leading-relaxed">{ans.justification}</p>
          </div>

          <div className="text-xs text-amber-600 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2 flex items-start gap-2">
            <AlertTriangle size={13} className="shrink-0 mt-0.5" />
            A resposta apoia a análise, mas não substitui revisão humana quando exigida pela política interna.
          </div>
        </div>
      </div>

      <ProvenancePanel rules={ans.rule_provenance ?? []} />

      {/* fontes */}
      {ans.sources?.length > 0 && (
        <div className="card mb-4">
          <div className="px-5 py-3 border-b border-slate-100">
            <p className="text-sm font-semibold text-slate-700">
              Fontes consultadas
              <span className="ml-2 text-xs font-normal text-slate-400">{ans.sources.length}</span>
            </p>
          </div>
          <div className="grid gap-3 p-4 lg:grid-cols-2">
            {ans.sources.map((s: any, i: number) => (
              <SourceCard key={i} source={s} />
            ))}
          </div>
        </div>
      )}

      {/* regras */}
      {ans.matched_rules?.length > 0 && (
        <div className="card mb-4 px-5 py-4">
          <p className="text-xs text-slate-500 mb-2">Regras aplicadas</p>
          <div className="flex flex-wrap gap-1.5">
            {ans.matched_rules.map((r: string) => (
              <span key={r} className="text-xs bg-slate-100 text-slate-600 px-2 py-0.5 rounded font-mono">
                {r}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* ações */}
      {(decision === "PRE_APPROVAL_REQUIRED" || ans.requires_human_review) && (
        <Link
          href={`/pre-approvals/new?from_query=${data.id}`}
          className="btn-primary text-sm inline-flex items-center gap-2"
        >
          <ClipboardCheck size={14} />
          {decision === "PRE_APPROVAL_REQUIRED" ? "Abrir pré-aprovação" : "Solicitar revisão humana"}
        </Link>
      )}
    </div>
  );
}
