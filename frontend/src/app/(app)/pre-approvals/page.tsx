"use client";

import { useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { ArrowRight, ClipboardCheck, Plus } from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { STATUS_CONFIG } from "@/lib/pre-approvals";
import { fmtCurrency, fmtDate } from "@/lib/utils";
import { PageHeader } from "@/components/layout/PageHeader";
import { Alert } from "@/components/ui/Alert";
import { EmptyState } from "@/components/ui/EmptyState";
import { FilterBar, TableFrame } from "@/components/ui/Panel";
import { Skeleton } from "@/components/ui/Skeleton";
import { StatusBadge } from "@/components/ui/StatusBadge";

const STATUS_OPTIONS = Object.entries(STATUS_CONFIG).map(([value, config]) => ({ value, label: config.label }));

export default function PreApprovalsPage() {
  const { user } = useAuth();
  const [status, setStatus] = useState("");
  const params = new URLSearchParams();
  if (status) params.set("status", status);
  const { data = [], isLoading, error, refetch } = useQuery({ queryKey: ["pre-approvals", status], queryFn: () => api.get(`/pre-approvals?${params}`).then(response => response.data) });
  const pending = data.filter((request: any) => ["PENDING", "IN_REVIEW"].includes(request.status)).length;
  const canCreate = user?.role !== "AUDITOR";

  return (
    <div>
      <PageHeader title="Fila de pré-aprovações" subtitle={`${data.length} solicitações no escopo · ${pending} aguardando andamento`} action={canCreate && <Link href="/pre-approvals/new" className="btn-primary"><Plus size={16} />Nova solicitação</Link>} />
      <FilterBar><label htmlFor="status-filter" className="text-xs font-semibold text-slate-600">Status</label><select id="status-filter" value={status} onChange={event => setStatus(event.target.value)} className="input w-full sm:w-56"><option value="">Todos os status</option>{STATUS_OPTIONS.map(option => <option key={option.value} value={option.value}>{option.label}</option>)}</select><span className="ml-auto text-xs tabular-nums text-slate-500">{data.length} resultados</span></FilterBar>
      {error ? <Alert variant="error">{(error as any).response?.data?.detail ?? "Não foi possível carregar as solicitações."}<button onClick={() => refetch()} className="ml-2 font-semibold underline underline-offset-2">Tentar novamente</button></Alert>
      : isLoading ? <TableSkeleton />
      : data.length === 0 ? <div className="card"><EmptyState message={status ? "Nenhuma solicitação corresponde ao filtro." : "Nenhuma pré-aprovação registrada."} icon={<ClipboardCheck size={28} />} />{canCreate && !status && <div className="flex justify-center border-t border-slate-200 p-4"><Link href="/pre-approvals/new" className="btn-secondary">Criar solicitação</Link></div>}</div>
      : <TableFrame><table><thead><tr><th>ID</th><th>Solicitante</th><th>Produto</th><th>Operação</th><th className="text-right">Valor</th><th>Status</th><th>Criada em</th><th>Responsável</th><th><span className="sr-only">Ação</span></th></tr></thead><tbody>{data.map((request: any) => <tr key={request.id}><td className="px-4 py-3 font-mono text-xs font-semibold text-slate-500">#{request.id}</td><td className="px-4 py-3 text-slate-600">Usuário #{request.requester_id}</td><td className="px-4 py-3"><p className="font-semibold text-slate-900">{request.product_label ?? `Produto #${request.product_id ?? "—"}`}</p>{request.intended_date && <p className="mt-0.5 text-xs text-slate-500">Pretendida em {fmtDate(request.intended_date)}</p>}</td><td className="px-4 py-3 text-slate-600">{request.operation_type}</td><td className="px-4 py-3 text-right tabular-nums text-slate-700">{request.estimated_amount ? fmtCurrency(request.estimated_amount) : "—"}</td><td className="px-4 py-3"><StatusBadge status={request.status} /></td><td className="px-4 py-3 whitespace-nowrap text-xs tabular-nums text-slate-500">{fmtDate(request.created_at)}</td><td className="px-4 py-3 text-xs text-slate-500">{request.reviewer ?? "Não atribuído"}</td><td className="px-4 py-3 text-right"><Link href={`/pre-approvals/${request.id}`} className="inline-flex items-center gap-1 text-sm font-semibold text-brand-700 hover:text-brand-900">Abrir<ArrowRight size={14} /></Link></td></tr>)}</tbody></table></TableFrame>}
    </div>
  );
}

function TableSkeleton() {
  return <div className="card p-4"><Skeleton className="mb-3 h-10 w-full" />{[1,2,3,4].map(row => <Skeleton key={row} className="mb-2 h-12 w-full" />)}</div>;
}
