"use client";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { PageHeader } from "@/components/layout/PageHeader";
import { Spinner } from "@/components/ui/Spinner";
import { MetricCard } from "@/components/ui/MetricCard";
import { DECISION_CONFIG, RISK_CONFIG } from "@/lib/copilot";
import { fmtCurrency } from "@/lib/utils";
import { Download } from "lucide-react";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
} from "recharts";

const PERIOD_OPTIONS = [
  { value: 7,  label: "7 dias" },
  { value: 30, label: "30 dias" },
  { value: 90, label: "3 meses" },
  { value: 180, label: "6 meses" },
];

const PA_STATUS_LABELS: Record<string,string> = {
  PENDING: "Pendente", IN_REVIEW: "Em análise", APPROVED: "Aprovado",
  APPROVED_WITH_CONDITIONS: "c/ ressalvas", REJECTED: "Rejeitado", CANCELLED: "Cancelado",
};

function SectionCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="card p-5">
      <h2 className="text-sm font-semibold text-slate-700 mb-4">{title}</h2>
      {children}
    </div>
  );
}

export default function ReportsPage() {
  const [days, setDays] = useState(30);

  const { data: summary, isLoading: loadSum } = useQuery({
    queryKey: ["report-summary", days],
    queryFn: () => api.get(`/reports/summary?days=${days}`).then((r) => r.data),
  });
  const { data: topProducts = [] } = useQuery({
    queryKey: ["report-products", days],
    queryFn: () => api.get(`/reports/top-products?days=${days}`).then((r) => r.data),
  });
  const { data: paByStatus = {} } = useQuery({
    queryKey: ["report-pa", days],
    queryFn: () => api.get(`/reports/pre-approvals-by-status?days=${days}`).then((r) => r.data),
  });
  const { data: topDocs = [] } = useQuery({
    queryKey: ["report-docs", days],
    queryFn: () => api.get(`/reports/top-documents?days=${days}`).then((r) => r.data),
  });
  const { data: topRules = [] } = useQuery({
    queryKey: ["report-rules", days],
    queryFn: () => api.get(`/reports/top-rules?days=${days}`).then((r) => r.data),
  });

  const exportCSV = () => {
    window.open(
      `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api"}/reports/export/csv?days=${days}`
    );
  };

  const decisionPie = Object.entries(summary?.by_decision ?? {}).map(([k, v]) => ({
    name: DECISION_CONFIG[k as keyof typeof DECISION_CONFIG]?.label ?? k,
    value: v as number,
  }));

  const riskPie = Object.entries(summary?.by_risk ?? {}).map(([k, v]) => ({
    name: RISK_CONFIG[k as keyof typeof RISK_CONFIG]?.label ?? k,
    value: v as number,
  }));

  const paPie = Object.entries(paByStatus).map(([k, v]) => ({
    name: PA_STATUS_LABELS[k] ?? k,
    value: v as number,
  }));

  return (
    <div>
      <PageHeader
        title="Relatórios"
        subtitle="Visão analítica do período selecionado"
        action={
          <div className="flex gap-2">
            <select value={days} onChange={(e) => setDays(Number(e.target.value))} className="input w-36 text-sm">
              {PERIOD_OPTIONS.map(({ value, label }) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
            <button onClick={exportCSV}
              className="flex items-center gap-2 text-sm border border-slate-200 hover:bg-slate-50 px-3 py-2 rounded-lg transition-colors">
              <Download size={14} /> Exportar CSV
            </button>
          </div>
        }
      />

      {loadSum ? (
        <div className="flex justify-center py-20"><Spinner className="h-8 w-8" /></div>
      ) : (
        <div className="space-y-6">
          {/* métricas */}
          <div className="grid grid-cols-1 gap-px overflow-hidden rounded-lg border border-slate-200 bg-slate-200 sm:grid-cols-2 lg:grid-cols-4 [&>*]:rounded-none [&>*]:border-0 [&>*]:shadow-none">
            <MetricCard label="Total de consultas" value={summary?.total_queries ?? 0} />
            <MetricCard label="Inconclusivas"
              value={`${summary?.inconclusive_count ?? 0} (${summary?.inconclusive_pct ?? 0}%)`}
              color="text-amber-500" />
            <MetricCard label="Pré-aprovações"
              value={Object.values(paByStatus as Record<string,number>).reduce((a, b) => a + b, 0)}
              color="text-brand-500" />
            <MetricCard label="Precisam revisão"
              value={summary?.by_decision?.["PRE_APPROVAL_REQUIRED"] ?? 0}
              color="text-amber-700" />
          </div>

          {/* consultas por dia + decisões */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <SectionCard title="Consultas por dia">
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={summary?.queries_by_day ?? []}>
                  <XAxis dataKey="date" tick={{ fontSize: 10 }} />
                  <YAxis tick={{ fontSize: 10 }} />
                  <Tooltip />
                  <Bar dataKey="count" fill="#176149" radius={[3,3,0,0]} />
                </BarChart>
              </ResponsiveContainer>
            </SectionCard>

            <SectionCard title="Decisões no período">
              <ResponsiveContainer width="100%" height={200}><BarChart data={decisionPie} layout="vertical" margin={{ left: 8 }}><XAxis type="number" allowDecimals={false} tick={{ fontSize: 10 }} /><YAxis type="category" dataKey="name" width={120} tick={{ fontSize: 10 }} /><Tooltip /><Bar dataKey="value" fill="#176149" radius={[0,3,3,0]} /></BarChart></ResponsiveContainer>
            </SectionCard>
          </div>

          {/* risco + pré-aprovações */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <SectionCard title="Distribuição de risco">
              <ResponsiveContainer width="100%" height={180}><BarChart data={riskPie} layout="vertical" margin={{ left: 8 }}><XAxis type="number" allowDecimals={false} tick={{ fontSize: 10 }} /><YAxis type="category" dataKey="name" width={72} tick={{ fontSize: 10 }} /><Tooltip /><Bar dataKey="value" fill="#50635b" radius={[0,3,3,0]} /></BarChart></ResponsiveContainer>
            </SectionCard>

            <SectionCard title="Pré-aprovações por status">
              {paPie.length === 0 ? (
                <p className="text-sm text-slate-400 text-center py-8">Sem dados no período.</p>
              ) : (
                <ResponsiveContainer width="100%" height={180}><BarChart data={paPie} layout="vertical" margin={{ left: 8 }}><XAxis type="number" allowDecimals={false} tick={{ fontSize: 10 }} /><YAxis type="category" dataKey="name" width={100} tick={{ fontSize: 10 }} /><Tooltip /><Bar dataKey="value" fill="#8a6a21" radius={[0,3,3,0]} /></BarChart></ResponsiveContainer>
              )}
            </SectionCard>
          </div>

          {/* tops */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <SectionCard title="Produtos mais consultados">
              {topProducts.length === 0 ? (
                <p className="text-sm text-slate-400 text-center py-6">Sem dados.</p>
              ) : (
                <div className="space-y-2">
                  {topProducts.map((p: any) => (
                    <div key={p.product_type} className="flex items-center justify-between text-sm">
                      <span className="text-slate-600 font-mono text-xs">{p.product_type}</span>
                      <span className="font-semibold text-slate-800">{p.count}</span>
                    </div>
                  ))}
                </div>
              )}
            </SectionCard>

            <SectionCard title="Documentos mais citados">
              {topDocs.length === 0 ? (
                <p className="text-sm text-slate-400 text-center py-6">Sem dados.</p>
              ) : (
                <div className="space-y-2">
                  {topDocs.map((d: any) => (
                    <div key={d.document_name} className="flex items-center justify-between text-sm">
                      <span className="text-slate-600 truncate max-w-[160px]" title={d.document_name}>
                        {d.document_name}
                      </span>
                      <span className="font-semibold text-slate-800 shrink-0 ml-2">{d.count}</span>
                    </div>
                  ))}
                </div>
              )}
            </SectionCard>

            <SectionCard title="Regras mais aplicadas">
              {topRules.length === 0 ? (
                <p className="text-sm text-slate-400 text-center py-6">Sem dados.</p>
              ) : (
                <div className="space-y-2">
                  {topRules.slice(0, 8).map((r: any) => (
                    <div key={r.rule} className="flex items-center justify-between text-sm">
                      <span className="text-slate-600 truncate max-w-[160px] text-xs" title={r.rule}>
                        {r.rule}
                      </span>
                      <span className="font-semibold text-slate-800 shrink-0 ml-2">{r.count}</span>
                    </div>
                  ))}
                </div>
              )}
            </SectionCard>
          </div>
        </div>
      )}
    </div>
  );
}
