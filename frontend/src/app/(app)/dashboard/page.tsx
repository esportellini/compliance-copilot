"use client";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { MetricCard } from "@/components/ui/MetricCard";
import { PageHeader } from "@/components/layout/PageHeader";
import { DecisionBadge } from "@/components/ui/DecisionBadge";
import { Spinner } from "@/components/ui/Spinner";
import { fmtDate } from "@/lib/utils";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";

export default function DashboardPage() {
  const { data, isLoading } = useQuery({ queryKey: ["dashboard"], queryFn: () => api.get("/dashboard").then(r => r.data) });

  if (isLoading) return <div className="flex items-center justify-center h-64"><Spinner className="h-8 w-8" /></div>;

  const byDecision = Object.entries(data?.by_decision ?? {}).map(([k, v]) => ({
    name: k, value: v as number,
  }));

  return (
    <div>
      <PageHeader title="Dashboard" subtitle="Visão geral do período atual" />
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <MetricCard label="Consultas este mês" value={data?.queries_this_month ?? 0} />
        <MetricCard label="Pré-aprovações pendentes" value={data?.pending_approvals ?? 0} color="text-amber-500" />
        <MetricCard label="Documentos ativos" value={data?.active_documents ?? 0} color="text-emerald-600" />
        <MetricCard label="Produtos restritos" value={data?.restricted_products ?? 0} color="text-red-500" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        <div className="card p-5">
          <h2 className="text-sm font-semibold text-slate-700 mb-4">Consultas por decisão (mês)</h2>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={byDecision}>
              <XAxis dataKey="name" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip />
              <Bar dataKey="value" fill="#3b5bdb" radius={[4,4,0,0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
        <div className="card p-5">
          <h2 className="text-sm font-semibold text-slate-700 mb-4">Consultas últimos 14 dias</h2>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={data?.queries_by_day ?? []}>
              <XAxis dataKey="date" tick={{ fontSize: 10 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip />
              <Bar dataKey="count" fill="#3b5bdb" radius={[4,4,0,0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="card">
        <div className="px-5 py-4 border-b border-slate-100">
          <h2 className="text-sm font-semibold text-slate-700">Consultas recentes</h2>
        </div>
        <div className="divide-y divide-slate-50">
          {(data?.recent_queries ?? []).map((q: any) => (
            <div key={q.id} className="px-5 py-3 flex items-center justify-between gap-4">
              <p className="text-sm text-slate-700 flex-1 truncate">{q.question}</p>
              {q.decision && <DecisionBadge decision={q.decision} />}
              <span className="text-xs text-slate-400 shrink-0">{fmtDate(q.created_at)}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}