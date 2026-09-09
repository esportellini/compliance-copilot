"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { ArrowRight, ClipboardCheck, FileCheck2, MessageSquareText, ShieldAlert } from "lucide-react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { DECISION_LABELS, fmtDate } from "@/lib/utils";
import { PageHeader } from "@/components/layout/PageHeader";
import { DecisionBadge } from "@/components/ui/DecisionBadge";
import { Alert } from "@/components/ui/Alert";
import { Panel, SectionHeader } from "@/components/ui/Panel";
import { Skeleton } from "@/components/ui/Skeleton";

export default function DashboardPage() {
  const { user } = useAuth();
  const { data, isLoading, isError, refetch } = useQuery({ queryKey: ["dashboard"], queryFn: () => api.get("/dashboard").then(r => r.data) });

  if (isLoading) return <DashboardSkeleton />;
  if (isError) return <Alert variant="error">Não foi possível carregar a visão geral. <button onClick={() => refetch()} className="ml-2 font-semibold underline underline-offset-2">Tentar novamente</button></Alert>;

  const byDecision = Object.entries(data?.by_decision ?? {}).map(([key, value]) => ({ name: DECISION_LABELS[key] ?? key, value: value as number }));
  const canQuery = user?.role !== "AUDITOR";
  const canReview = user?.role === "ADMIN" || user?.role === "COMPLIANCE";

  return (
    <div>
      <PageHeader title="Visão geral" subtitle="Atividade, decisões e pendências dentro do seu escopo de acesso." action={canQuery && <Link href="/copilot" className="btn-primary"><MessageSquareText size={16} />Nova consulta</Link>} />

      <section className="mb-7 grid border-y border-slate-200 bg-white sm:grid-cols-2 xl:grid-cols-4" aria-label="Resumo operacional">
        <Metric label="Consultas neste mês" value={data?.queries_this_month ?? 0} icon={<MessageSquareText size={16} />} />
        <Metric label="Pré-aprovações pendentes" value={data?.pending_approvals ?? 0} icon={<ClipboardCheck size={16} />} attention={Boolean(data?.pending_approvals)} />
        <Metric label="Documentos ativos" value={data?.active_documents ?? 0} icon={<FileCheck2 size={16} />} />
        <Metric label="Produtos restritos" value={data?.restricted_products ?? 0} icon={<ShieldAlert size={16} />} attention={Boolean(data?.restricted_products)} last />
      </section>

      <div className="mb-7 grid gap-6 xl:grid-cols-[1.45fr_0.75fr]">
        <Panel>
          <SectionHeader title="Distribuição das decisões" description="Consultas registradas no mês atual." />
          <div className="h-[270px] p-5">
            {byDecision.length ? <ResponsiveContainer width="100%" height="100%"><BarChart data={byDecision} layout="vertical" margin={{ left: 8, right: 12 }}><CartesianGrid stroke="#e4e8e3" horizontal={false} /><XAxis type="number" tick={{ fontSize: 11, fill: "#6e7b73" }} allowDecimals={false} /><YAxis dataKey="name" type="category" width={128} tick={{ fontSize: 11, fill: "#49574f" }} /><Tooltip cursor={{ fill: "#eef7f2" }} contentStyle={{ border: "1px solid #d9ded7", borderRadius: 8, fontSize: 12 }} /><Bar dataKey="value" fill="#176149" radius={[0, 4, 4, 0]} maxBarSize={24} /></BarChart></ResponsiveContainer> : <div className="flex h-full items-center justify-center text-sm text-slate-500">Ainda não há decisões neste período.</div>}
          </div>
        </Panel>

        <Panel className="flex flex-col">
          <SectionHeader title="Atenção operacional" description={canReview ? "Fila disponível para sua equipe." : "Itens que dependem de acompanhamento."} />
          <div className="flex flex-1 flex-col p-5">
            <div className="flex items-start gap-3 rounded-lg bg-amber-50 p-4 text-amber-950 ring-1 ring-inset ring-amber-700/15">
              <ClipboardCheck size={19} className="mt-0.5 shrink-0 text-amber-700" />
              <div><p className="text-sm font-semibold">{data?.pending_approvals ?? 0} solicitações pendentes</p><p className="mt-1 text-xs leading-5 text-amber-800">{canReview ? "Revise a fila e registre o próximo passo." : "Acompanhe o andamento das suas solicitações."}</p></div>
            </div>
            <Link href="/pre-approvals" className="btn-secondary mt-auto w-full">Abrir fila<ArrowRight size={15} /></Link>
          </div>
        </Panel>
      </div>

      <Panel>
        <SectionHeader title="Atividade recente" description="Últimas consultas registradas no seu escopo." action={<Link href="/history" className="text-sm font-semibold text-brand-700 hover:text-brand-900">Ver histórico</Link>} />
        {(data?.recent_queries ?? []).length ? <div className="divide-y divide-slate-100">{data.recent_queries.map((query: any) => <Link href={`/history/${query.id}`} key={query.id} className="grid gap-3 px-5 py-4 hover:bg-brand-50/40 sm:grid-cols-[minmax(0,1fr)_auto_auto] sm:items-center"><div className="min-w-0"><p className="truncate text-sm font-medium text-slate-800">{query.question}</p><p className="mt-1 font-mono text-[11px] text-slate-400">Consulta #{query.id}</p></div>{query.decision && <DecisionBadge decision={query.decision} />}<time className="text-xs tabular-nums text-slate-500">{fmtDate(query.created_at)}</time></Link>)}</div> : <div className="px-5 py-12 text-center"><MessageSquareText className="mx-auto text-slate-300" size={24} /><p className="mt-3 text-sm font-medium text-slate-700">Nenhuma consulta recente</p><p className="mt-1 text-xs text-slate-500">A atividade aparecerá aqui assim que houver registros.</p></div>}
      </Panel>
    </div>
  );
}

function Metric({ label, value, icon, attention, last }: { label: string; value: number; icon: React.ReactNode; attention?: boolean; last?: boolean }) {
  return <div className={`px-5 py-5 sm:px-6 ${last ? "" : "border-b border-slate-200 sm:border-b-0 sm:border-r"}`}><div className="mb-3 flex items-center justify-between text-slate-500"><p className="text-[11px] font-semibold uppercase tracking-[0.08em]">{label}</p><span className={attention ? "text-amber-700" : "text-brand-700"}>{icon}</span></div><p className={`text-3xl font-semibold tabular-nums tracking-[-0.04em] ${attention ? "text-amber-800" : "text-slate-950"}`}>{value}</p></div>;
}

function DashboardSkeleton() {
  return <div><Skeleton className="mb-7 h-20 w-full" /><div className="mb-7 grid gap-px bg-slate-200 sm:grid-cols-4">{[1,2,3,4].map(i => <Skeleton key={i} className="h-28 rounded-none bg-white" />)}</div><div className="grid gap-6 xl:grid-cols-2"><Skeleton className="h-80" /><Skeleton className="h-80" /></div></div>;
}
