"use client";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useParams } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { PageHeader } from "@/components/layout/PageHeader";
import { Alert } from "@/components/ui/Alert";
import { Spinner } from "@/components/ui/Spinner";
import { DecisionBadge } from "@/components/ui/DecisionBadge";
import { DOC_TYPE_MAP, STATUS_BADGE, STATUS_MAP, fmtSize } from "@/lib/documents";
import { fmtDate, fmtDateTime } from "@/lib/utils";
import { ChevronLeft, RefreshCw, Archive, Play, X } from "lucide-react";

function ConfirmModal({ title, body, confirmLabel, confirmClass, onConfirm, onClose, isPending }: {
  title: string; body: string; confirmLabel: string; confirmClass: string;
  onConfirm: () => void; onClose: () => void; isPending: boolean;
}) {
  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-sm">
        <div className="flex items-start justify-between px-6 py-4 border-b border-slate-100">
          <h2 className="font-semibold text-slate-800">{title}</h2>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600 ml-4"><X size={18} /></button>
        </div>
        <div className="px-6 py-5">
          <p className="text-sm text-slate-600">{body}</p>
          <div className="flex justify-end gap-3 mt-6">
            <button onClick={onClose} className="btn-ghost text-sm">Cancelar</button>
            <button onClick={onConfirm} disabled={isPending}
              className={`text-sm font-medium px-4 py-2 rounded-lg text-white transition-colors flex items-center gap-2 ${confirmClass}`}>
              {isPending && <Spinner className="h-4 w-4 border-white border-t-transparent" />}
              {confirmLabel}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function DetailRow({ label, value }: { label: string; value?: string | number | null }) {
  if (value === null || value === undefined || value === "") return null;
  return (
    <div className="flex gap-2">
      <span className="w-40 shrink-0 text-xs text-slate-500 pt-0.5">{label}</span>
      <span className="text-sm text-slate-800">{String(value)}</span>
    </div>
  );
}

export default function DocumentDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();
  const qc = useQueryClient();
  const canEdit = user && ["ADMIN", "COMPLIANCE"].includes(user.role);

  const [confirm, setConfirm]     = useState<"process" | "reprocess" | "archive" | null>(null);
  const [actionError, setAErr]    = useState("");

  const { data: doc, isLoading } = useQuery({
    queryKey: ["document", id],
    queryFn: () => api.get(`/documents/${id}`).then((r) => r.data),
  });

  const { data: chunks = [] } = useQuery({
    queryKey: ["document-chunks", id],
    queryFn: () => api.get(`/documents/${id}/chunks`).then((r) => r.data),
    enabled: !!id,
  });

  const { data: queries = [] } = useQuery({
    queryKey: ["document-queries", id],
    queryFn: async () => {
      // busca consultas que referenciam este documento via source_references
      // endpoint simplificado: filtra histórico pelo doc id
      const all = await api.get("/copilot/history").then((r) => r.data);
      return all.slice(0, 5); // placeholder — mostra recentes
    },
    enabled: !!id,
  });

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["document", id] });
    qc.invalidateQueries({ queryKey: ["document-chunks", id] });
    qc.invalidateQueries({ queryKey: ["documents"] });
  };

  const processMutation = useMutation({
    mutationFn: () => api.post(`/documents/${id}/process`),
    onSuccess: () => { invalidate(); setConfirm(null); setAErr(""); },
    onError: (e: any) => { setAErr(e.response?.data?.detail ?? "Erro ao processar"); setConfirm(null); },
  });

  const archiveMutation = useMutation({
    mutationFn: () => api.post(`/documents/${id}/archive`),
    onSuccess: () => { invalidate(); setConfirm(null); setAErr(""); },
    onError: (e: any) => { setAErr(e.response?.data?.detail ?? "Erro ao arquivar"); setConfirm(null); },
  });

  if (isLoading) return <div className="flex justify-center py-20"><Spinner className="h-8 w-8" /></div>;
  if (!doc) return <Alert variant="error">Documento não encontrado.</Alert>;

  const isArchived  = doc.status === "ARCHIVED";
  const isActive    = doc.status === "ACTIVE";
  const isDraft     = doc.status === "DRAFT";
  const canActivate = !isArchived && doc.version && doc.owner;

  const statusBadge = STATUS_BADGE[doc.status] ?? "bg-slate-100 text-slate-600";

  return (
    <div className="max-w-3xl">
      <div className="flex items-center gap-2 text-sm text-slate-500 mb-4">
        <Link href="/documents" className="hover:text-brand-600 flex items-center gap-1">
          <ChevronLeft size={14} /> Documentos
        </Link>
        <span>/</span>
        <span className="text-slate-700">{doc.name}</span>
      </div>

      <PageHeader
        title={doc.name}
        subtitle={DOC_TYPE_MAP[doc.doc_type] ?? doc.doc_type}
        action={
          canEdit && !isArchived && (
            <div className="flex gap-2">
              <button onClick={() => setConfirm("archive")}
                className="flex items-center gap-1.5 text-sm text-amber-600 border border-amber-200 hover:bg-amber-50 px-3 py-2 rounded-lg transition-colors">
                <Archive size={14} /> Arquivar
              </button>
              {isActive ? (
                <button onClick={() => setConfirm("reprocess")}
                  className="flex items-center gap-1.5 text-sm border border-slate-200 hover:bg-slate-50 px-3 py-2 rounded-lg transition-colors">
                  <RefreshCw size={14} /> Reprocessar
                </button>
              ) : (
                <button onClick={() => setConfirm("process")} disabled={!canActivate}
                  title={!canActivate ? "Defina versão e responsável primeiro" : undefined}
                  className="btn-primary text-sm flex items-center gap-1.5 disabled:opacity-40">
                  <Play size={14} /> Processar
                </button>
              )}
            </div>
          )
        }
      />

      {/* badges */}
      <div className="flex items-center gap-2 mb-6 flex-wrap">
        <span className={`text-xs font-medium px-2.5 py-1 rounded-full ${statusBadge}`}>
          {STATUS_MAP[doc.status] ?? doc.status}
        </span>
        {doc.version && (
          <span className="text-xs bg-slate-100 text-slate-600 px-2.5 py-1 rounded-full font-mono">
            v{doc.version}
          </span>
        )}
        {doc.chunk_count > 0 && (
          <span className="text-xs bg-brand-50 text-brand-700 px-2.5 py-1 rounded-full">
            {doc.chunk_count} chunks
          </span>
        )}
      </div>

      {actionError && <Alert variant="error" className="mb-4">{actionError}</Alert>}

      {!doc.version || !doc.owner ? (
        <Alert variant="warning" className="mb-4">
          Para processar este documento, defina <strong>versão</strong> e <strong>responsável</strong> primeiro.{" "}
          <Link href={`/documents/${id}/edit`} className="underline">Editar metadados</Link>
        </Alert>
      ) : null}

      {/* dados */}
      <div className="card p-6 mb-6">
        <h2 className="text-sm font-semibold text-slate-700 mb-4">Dados do documento</h2>
        <div className="space-y-2.5">
          <DetailRow label="Responsável"    value={doc.owner} />
          <DetailRow label="Vigência"       value={doc.effective_date ? fmtDate(doc.effective_date) : null} />
          <DetailRow label="Arquivo original" value={doc.original_filename} />
          <DetailRow label="Tamanho"        value={doc.file_size_bytes ? fmtSize(doc.file_size_bytes) : null} />
          <DetailRow label="Enviado em"     value={doc.uploaded_at ? fmtDateTime(doc.uploaded_at) : null} />
          <DetailRow label="Processado em"  value={doc.processed_at ? fmtDateTime(doc.processed_at) : null} />
          <DetailRow label="Cadastrado em"  value={fmtDateTime(doc.created_at)} />
        </div>
      </div>

      {/* chunks */}
      <div className="card mb-6">
        <div className="px-5 py-4 border-b border-slate-100">
          <h2 className="text-sm font-semibold text-slate-700">
            Chunks indexados
            <span className="ml-2 text-xs font-normal text-slate-400">{chunks.length}</span>
          </h2>
        </div>
        {chunks.length === 0 ? (
          <p className="px-5 py-8 text-sm text-slate-400 text-center">
            {isDraft ? "Processe o documento para gerar os chunks." : "Nenhum chunk gerado."}
          </p>
        ) : (
          <div className="divide-y divide-slate-50 max-h-96 overflow-y-auto">
            {chunks.map((c: any) => (
              <div key={c.id} className="px-5 py-3">
                <div className="flex items-center gap-3 mb-1">
                  <span className="text-xs font-mono text-slate-400">#{c.chunk_index + 1}</span>
                  {c.page_number && (
                    <span className="text-xs bg-slate-100 text-slate-500 px-1.5 py-0.5 rounded">
                      pág. {c.page_number}
                    </span>
                  )}
                  {c.section_title && (
                    <span className="text-xs text-slate-500 italic truncate max-w-xs">{c.section_title}</span>
                  )}
                  <span className="text-xs text-slate-300 ml-auto">{c.char_count} chars</span>
                </div>
                <p className="text-xs text-slate-600 line-clamp-3">{c.content}</p>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* consultas recentes (placeholder) */}
      <div className="card">
        <div className="px-5 py-4 border-b border-slate-100">
          <h2 className="text-sm font-semibold text-slate-700">Consultas que citaram este documento</h2>
        </div>
        <p className="px-5 py-8 text-sm text-slate-400 text-center">
          As consultas que citam este documento aparecem no histórico do Copilot.{" "}
          <Link href="/history" className="text-brand-600 hover:underline">Ver histórico</Link>
        </p>
      </div>

      {/* modais de confirmação */}
      {confirm === "process" && (
        <ConfirmModal
          title="Processar documento"
          body={`Isso irá extrair o texto, gerar chunks e ativar "${doc.name}" como fonte para o Copilot. Confirmar?`}
          confirmLabel="Processar"
          confirmClass="bg-brand-500 hover:bg-brand-600"
          onConfirm={() => processMutation.mutate()}
          onClose={() => setConfirm(null)}
          isPending={processMutation.isPending}
        />
      )}
      {confirm === "reprocess" && (
        <ConfirmModal
          title="Reprocessar documento"
          body={`Os chunks atuais serão descartados e gerados novamente a partir do texto extraído. Continuar?`}
          confirmLabel="Reprocessar"
          confirmClass="bg-brand-500 hover:bg-brand-600"
          onConfirm={() => processMutation.mutate()}
          onClose={() => setConfirm(null)}
          isPending={processMutation.isPending}
        />
      )}
      {confirm === "archive" && (
        <ConfirmModal
          title="Arquivar documento"
          body={`"${doc.name}" será marcado como arquivado e não será usado como fonte principal pelo Copilot. Esta ação gera registro de auditoria.`}
          confirmLabel="Arquivar"
          confirmClass="bg-amber-500 hover:bg-amber-600"
          onConfirm={() => archiveMutation.mutate()}
          onClose={() => setConfirm(null)}
          isPending={archiveMutation.isPending}
        />
      )}
    </div>
  );
}