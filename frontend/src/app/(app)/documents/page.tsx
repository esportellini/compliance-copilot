"use client";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { PageHeader } from "@/components/layout/PageHeader";
import { Spinner } from "@/components/ui/Spinner";
import { EmptyState } from "@/components/ui/EmptyState";
import { DOCUMENT_TYPES, DOC_TYPE_MAP, STATUS_OPTIONS, STATUS_BADGE, STATUS_MAP, fmtSize } from "@/lib/documents";
import { fmtDate } from "@/lib/utils";
import { FileText } from "lucide-react";

export default function DocumentsPage() {
  const { user } = useAuth();
  const canEdit = user && ["ADMIN", "COMPLIANCE"].includes(user.role);

  const [statusF, setStatusF]     = useState("");
  const [typeF, setTypeF]         = useState("");
  const [archived, setArchived]   = useState(false);

  const params = new URLSearchParams();
  if (statusF)  params.set("status", statusF);
  if (typeF)    params.set("doc_type", typeF);
  if (archived) params.set("include_archived", "true");

  const { data: docs = [], isLoading } = useQuery({
    queryKey: ["documents", statusF, typeF, archived],
    queryFn: () => api.get(`/documents?${params}`).then((r) => r.data),
  });

  return (
    <div>
      <PageHeader
        title="Documentos"
        subtitle={`${docs.length} documento${docs.length !== 1 ? "s" : ""}`}
        action={
          canEdit && (
            <Link href="/documents/upload" className="btn-primary text-sm">
              + Enviar documento
            </Link>
          )
        }
      />

      <div className="flex flex-wrap gap-3 mb-6">
        <select value={typeF} onChange={(e) => setTypeF(e.target.value)} className="input w-64">
          <option value="">Tipo</option>
          {DOCUMENT_TYPES.map(({ value, label }) => (
            <option key={value} value={value}>{label}</option>
          ))}
        </select>

        <select value={statusF} onChange={(e) => setStatusF(e.target.value)} className="input w-40">
          <option value="">Status</option>
          {STATUS_OPTIONS.map(({ value, label }) => (
            <option key={value} value={value}>{label}</option>
          ))}
        </select>

        <label className="flex items-center gap-2 text-sm text-slate-600 cursor-pointer select-none px-3 py-2 rounded-lg hover:bg-slate-100">
          <input type="checkbox" checked={archived} onChange={(e) => setArchived(e.target.checked)}
            className="rounded border-slate-300" />
          Incluir arquivados
        </label>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-20"><Spinner className="h-8 w-8" /></div>
      ) : docs.length === 0 ? (
        <EmptyState message="Nenhum documento encontrado." icon={<FileText />} />
      ) : (
        <div className="card overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-xs text-slate-500 uppercase tracking-wide">
              <tr>
                <th className="px-4 py-3 text-left">Nome</th>
                <th className="px-4 py-3 text-left">Tipo</th>
                <th className="px-4 py-3 text-left">Versão</th>
                <th className="px-4 py-3 text-left">Status</th>
                <th className="px-4 py-3 text-left">Responsável</th>
                <th className="px-4 py-3 text-right">Chunks</th>
                <th className="px-4 py-3 text-left">Processado</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {docs.map((d: any) => (
                <tr key={d.id} className={`hover:bg-slate-50 transition-colors ${d.status === "ARCHIVED" ? "opacity-50" : ""}`}>
                  <td className="px-4 py-3">
                    <Link href={`/documents/${d.id}`} className="font-medium text-brand-600 hover:underline">
                      {d.name}
                    </Link>
                    {d.original_filename && (
                      <p className="text-xs text-slate-400 mt-0.5">
                        {d.original_filename}
                        {d.file_size_bytes ? ` · ${fmtSize(d.file_size_bytes)}` : ""}
                      </p>
                    )}
                  </td>
                  <td className="px-4 py-3 text-slate-500">{DOC_TYPE_MAP[d.doc_type] ?? d.doc_type}</td>
                  <td className="px-4 py-3 font-mono text-xs text-slate-600">{d.version ?? "—"}</td>
                  <td className="px-4 py-3">
                    <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${STATUS_BADGE[d.status] ?? "bg-slate-100"}`}>
                      {STATUS_MAP[d.status] ?? d.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-slate-500">{d.owner ?? "—"}</td>
                  <td className="px-4 py-3 text-right tabular-nums text-slate-500">{d.chunk_count}</td>
                  <td className="px-4 py-3 text-slate-500 text-xs">
                    {d.processed_at ? fmtDate(d.processed_at) : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}