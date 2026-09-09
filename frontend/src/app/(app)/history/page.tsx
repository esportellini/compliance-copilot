"use client";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { api } from "@/lib/api";
import { PageHeader } from "@/components/layout/PageHeader";
import { Spinner } from "@/components/ui/Spinner";
import { EmptyState } from "@/components/ui/EmptyState";
import { DecisionBadge } from "@/components/ui/DecisionBadge";
import { RiskBadge } from "@/components/ui/RiskBadge";
import { SkeletonRows } from "@/components/ui/Skeleton";
import { DECISION_CONFIG, RISK_CONFIG, PRODUCT_TYPES } from "@/lib/copilot";
import { fmtDateTime, fmtCurrency } from "@/lib/utils";
import { History, AlertTriangle, X } from "lucide-react";

const DECISIONS = Object.entries(DECISION_CONFIG).map(([value, cfg]) => ({
  value, label: cfg.label,
}));
const RISKS = Object.entries(RISK_CONFIG).map(([value, cfg]) => ({
  value, label: cfg.label,
}));

export default function HistoryPage() {
  const [decisionF, setDecision]   = useState("");
  const [riskF, setRisk]           = useState("");
  const [typeF, setType]           = useState("");
  const [dateFrom, setDateFrom]    = useState("");
  const [dateTo, setDateTo]        = useState("");

  const params = new URLSearchParams();
  if (decisionF) params.set("decision", decisionF);
  if (riskF)     params.set("risk_level", riskF);
  if (typeF)     params.set("product_type", typeF);
  if (dateFrom)  params.set("date_from", dateFrom);
  if (dateTo)    params.set("date_to", dateTo + "T23:59:59");

  const { data = [], isLoading } = useQuery({
    queryKey: ["history", decisionF, riskF, typeF, dateFrom, dateTo],
    queryFn: () => api.get(`/copilot/history?${params}`).then((r) => r.data),
  });

  const hasFilters = decisionF || riskF || typeF || dateFrom || dateTo;
  const clearFilters = () => {
    setDecision(""); setRisk(""); setType(""); setDateFrom(""); setDateTo("");
  };

  return (
    <div>
      <PageHeader
        title="Histórico de Consultas"
        subtitle={`${data.length} consulta${data.length !== 1 ? "s" : ""}`}
      />

      {/* filtros */}
      <div className="mb-5 flex flex-wrap gap-3 rounded-lg border border-slate-200 bg-white p-3">
        <select value={decisionF} onChange={(e) => setDecision(e.target.value)} className="input w-44">
          <option value="">Decisão</option>
          {DECISIONS.map(({ value, label }) => (
            <option key={value} value={value}>{label}</option>
          ))}
        </select>

        <select value={riskF} onChange={(e) => setRisk(e.target.value)} className="input w-36">
          <option value="">Risco</option>
          {RISKS.map(({ value, label }) => (
            <option key={value} value={value}>{label}</option>
          ))}
        </select>

        <select value={typeF} onChange={(e) => setType(e.target.value)} className="input w-44">
          <option value="">Tipo de produto</option>
          {PRODUCT_TYPES.map(({ value, label }) => (
            <option key={value} value={value}>{label}</option>
          ))}
        </select>

        <input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)}
          className="input w-40" title="De" />
        <input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)}
          className="input w-40" title="Até" />

        {hasFilters && (
          <button onClick={clearFilters}
            className="flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-700 px-3 py-2 rounded-lg hover:bg-slate-100 transition-colors">
            <X size={14} /> Limpar
          </button>
        )}
      </div>

      {isLoading ? (
        <div className="card p-4"><SkeletonRows rows={7} /></div>
      ) : data.length === 0 ? (
        <EmptyState
          message={hasFilters ? "Nenhuma consulta corresponde aos filtros." : "Nenhuma consulta realizada."}
          icon={<History />}
        />
      ) : (
        <div className="card overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-xs text-slate-500 uppercase tracking-wide">
              <tr>
                <th className="px-4 py-3 text-left">Pergunta</th>
                <th className="px-4 py-3 text-left">Produto</th>
                <th className="px-4 py-3 text-left">Valor</th>
                <th className="px-4 py-3 text-left">Decisão</th>
                <th className="px-4 py-3 text-left">Risco</th>
                <th className="px-4 py-3 text-right">Conf.</th>
                <th className="px-4 py-3 text-left">Data</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {data.map((q: any) => {
                return (
                  <tr key={q.id} className="hover:bg-slate-50 transition-colors">
                    <td className="px-4 py-3 max-w-xs">
                      <Link href={`/history/${q.id}`}
                        className="text-brand-600 hover:underline line-clamp-2 leading-snug">
                        {q.question}
                      </Link>
                      {q.requires_human_review && (
                        <span className="inline-flex items-center gap-0.5 mt-1 text-xs text-amber-600">
                          <AlertTriangle size={11} /> revisão
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-xs"><p className="font-mono font-semibold text-slate-800">{q.product_identifier ?? "—"}</p><p className="mt-0.5 text-slate-500">{q.product_label ?? q.product_type ?? "Produto não informado"}</p></td>
                    <td className="px-4 py-3 text-slate-500 text-xs">
                      {q.amount ? fmtCurrency(q.amount) : "—"}
                    </td>
                    <td className="px-4 py-3">
                      <DecisionBadge decision={q.decision} />
                    </td>
                    <td className="px-4 py-3">
                      <RiskBadge risk={q.risk_level} />
                    </td>
                    <td className="px-4 py-3 text-right tabular-nums text-slate-500 text-xs">
                      {Math.round(q.confidence * 100)}%
                    </td>
                    <td className="px-4 py-3 text-slate-500 text-xs whitespace-nowrap">
                      {fmtDateTime(q.created_at)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
