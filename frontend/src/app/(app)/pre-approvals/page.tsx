"use client";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { PageHeader } from "@/components/layout/PageHeader";
import { Spinner } from "@/components/ui/Spinner";
import { EmptyState } from "@/components/ui/EmptyState";
import { STATUS_CONFIG, type StatusKey } from "@/lib/pre-approvals";
import { fmtDate, fmtCurrency } from "@/lib/utils";
import { ClipboardCheck } from "lucide-react";

const STATUS_OPTS = Object.entries(STATUS_CONFIG).map(([v, c]) => ({ value: v, label: c.label }));

export default function PreApprovalsPage() {
  const { user } = useAuth();
  const [statusF, setStatus] = useState("");

  const params = new URLSearchParams();
  if (statusF) params.set("status", statusF);

  const { data = [], isLoading } = useQuery({
    queryKey: ["pre-approvals", statusF],
    queryFn: () => api.get(`/pre-approvals?${params}`).then((r) => r.data),
  });

  const pending = data.filter((r: any) => ["PENDING","IN_REVIEW"].includes(r.status)).length;

  return (
    <div>
      <PageHeader
        title="Pré-aprovações"
        subtitle={`${data.length} solicitaç${data.length !== 1 ? "ões" : "ão"}${pending ? ` · ${pending} pendente${pending !== 1 ? "s" : ""}` : ""}`}
        action={<Link href="/pre-approvals/new" className="btn-primary text-sm">+ Nova solicitação</Link>}
      />

      <div className="flex gap-3 mb-6">
        <select value={statusF} onChange={(e) => setStatus(e.target.value)} className="input w-52">
          <option value="">Todos os status</option>
          {STATUS_OPTS.map(({ value, label }) => (
            <option key={value} value={value}>{label}</option>
          ))}
        </select>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-20"><Spinner className="h-8 w-8" /></div>
      ) : data.length === 0 ? (
        <EmptyState message="Nenhuma solicitação encontrada." icon={<ClipboardCheck />} />
      ) : (
        <div className="card overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-xs text-slate-500 uppercase tracking-wide">
              <tr>
                <th className="px-4 py-3 text-left">Produto</th>
                <th className="px-4 py-3 text-left">Operação</th>
                <th className="px-4 py-3 text-left">Valor</th>
                <th className="px-4 py-3 text-left">Status</th>
                <th className="px-4 py-3 text-left">Data pretendida</th>
                <th className="px-4 py-3 text-left">Solicitado em</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {data.map((r: any) => {
                const cfg = STATUS_CONFIG[r.status as StatusKey] ?? STATUS_CONFIG.PENDING;
                return (
                  <tr key={r.id} className="hover:bg-slate-50 transition-colors">
                    <td className="px-4 py-3">
                      <Link href={`/pre-approvals/${r.id}`} className="font-medium text-brand-600 hover:underline">
                        {r.product_label ?? `Produto #${r.product_id ?? "—"}`}
                      </Link>
                    </td>
                    <td className="px-4 py-3 text-slate-600">{r.operation_type}</td>
                    <td className="px-4 py-3">{r.estimated_amount ? fmtCurrency(r.estimated_amount) : "—"}</td>
                    <td className="px-4 py-3">
                      <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${cfg.badge}`}>{cfg.label}</span>
                    </td>
                    <td className="px-4 py-3 text-slate-500 text-xs">{r.intended_date ? fmtDate(r.intended_date) : "—"}</td>
                    <td className="px-4 py-3 text-slate-500 text-xs">{fmtDate(r.created_at)}</td>
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