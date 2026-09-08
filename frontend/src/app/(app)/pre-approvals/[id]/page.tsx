"use client";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useParams } from "next/navigation";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { PageHeader } from "@/components/layout/PageHeader";
import { Alert } from "@/components/ui/Alert";
import { Spinner } from "@/components/ui/Spinner";
import { STATUS_CONFIG, type StatusKey } from "@/lib/pre-approvals";
import { fmtCurrency, fmtDate, fmtDateTime } from "@/lib/utils";
import { ChevronLeft, Send } from "lucide-react";

const TERMINAL = ["APPROVED","APPROVED_WITH_CONDITIONS","REJECTED","CANCELLED"];

const decisionSchema = z.object({
  status: z.enum(["IN_REVIEW","APPROVED","APPROVED_WITH_CONDITIONS","REJECTED","CANCELLED"]),
  compliance_opinion: z.string().optional(),
}).superRefine((value, ctx) => {
  if (["APPROVED", "APPROVED_WITH_CONDITIONS", "REJECTED"].includes(value.status)
      && !value.compliance_opinion?.trim()) {
    ctx.addIssue({ code: z.ZodIssueCode.custom, path: ["compliance_opinion"], message: "Parecer obrigatório" });
  }
});
type DecisionForm = z.infer<typeof decisionSchema>;

const commentSchema = z.object({ body: z.string().trim().min(1, "Escreva um comentário") });
type CommentForm = z.infer<typeof commentSchema>;

// ─── timeline ─────────────────────────────────────────────────────────────────
function Timeline({ request }: { request: any }) {
  const events = [
    { key: "created", label: "Solicitação criada", at: request.created_at },
    ...(request.copilot_initial_response ? [{ key: "analysis", label: `Análise inicial: ${request.copilot_initial_decision ?? "registrada"}`, at: request.created_at }] : []),
    ...(request.review_started_at ? [{ key: "review", label: "Revisão iniciada", at: request.review_started_at }] : []),
    ...(request.comments ?? []).map((comment: any) => ({ key: `comment-${comment.id}`, label: `Comentário de ${comment.author_name}`, at: comment.created_at })),
    ...(request.decided_at ? [{ key: "decision", label: `Decisão final: ${(STATUS_CONFIG[request.status as StatusKey] ?? STATUS_CONFIG.PENDING).label}`, at: request.decided_at }] : []),
    ...(request.status === "CANCELLED" ? [{ key: "cancelled", label: "Solicitação cancelada", at: request.updated_at }] : []),
  ].sort((a, b) => new Date(a.at).getTime() - new Date(b.at).getTime());
  return (
    <div className="card p-5 mb-6">
      <h3 className="text-sm font-semibold text-slate-700 mb-3">Timeline</h3>
      <div className="space-y-3">
        {events.map((event) => (
          <div key={event.key} className="flex gap-3 text-sm">
            <div className="mt-1 h-2 w-2 rounded-full bg-brand-500 shrink-0" />
            <div>
              <p className="text-slate-700">{event.label}</p>
              <p className="text-xs text-slate-400">{fmtDateTime(event.at)}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── página ────────────────────────────────────────────────────────────────────
export default function PreApprovalDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();
  const qc = useQueryClient();
  const canDecide = user && ["ADMIN","COMPLIANCE"].includes(user.role);
  const canComment = user?.role !== "AUDITOR";
  const isTerminal = (status: string) => TERMINAL.includes(status);

  const [showDecision, setShowDecision] = useState(false);
  const [actionError, setActionError] = useState("");

  const { data: req, isLoading, error: loadError } = useQuery({
    queryKey: ["pre-approval", id],
    queryFn: () => api.get(`/pre-approvals/${id}`).then((r) => r.data),
  });

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["pre-approval", id] });
    qc.invalidateQueries({ queryKey: ["pre-approvals"] });
  };

  const decisionForm = useForm<DecisionForm>({
    resolver: zodResolver(decisionSchema),
    defaultValues: { status: "IN_REVIEW" },
  });

  const commentForm = useForm<CommentForm>({ resolver: zodResolver(commentSchema) });

  const decisionMutation = useMutation({
    mutationFn: (d: DecisionForm) => api.patch(`/pre-approvals/${id}/status`, d),
    onSuccess: () => { invalidate(); setShowDecision(false); setActionError(""); },
    onError: (e: any) => setActionError(e.response?.data?.detail ?? "Erro"),
  });

  const commentMutation = useMutation({
    mutationFn: (d: CommentForm) => api.post(`/pre-approvals/${id}/comments`, d),
    onSuccess: () => { invalidate(); commentForm.reset(); },
    onError: (e: any) => setActionError(e.response?.data?.detail ?? "Erro ao comentar"),
  });

  if (isLoading) return <div className="flex justify-center py-20"><Spinner className="h-8 w-8" /></div>;
  if (loadError || !req) return (
    <Alert variant="error">
      {(loadError as any)?.response?.data?.detail ?? "Não foi possível carregar a solicitação."}
    </Alert>
  );

  const cfg = STATUS_CONFIG[req.status as StatusKey] ?? STATUS_CONFIG.PENDING;
  const statusOptions = req.status === "PENDING"
    ? ["IN_REVIEW", "REJECTED", "CANCELLED"]
    : ["APPROVED", "APPROVED_WITH_CONDITIONS", "REJECTED", "CANCELLED"];
  const canEmployeeCancel = user?.role === "EMPLOYEE" && req.status === "PENDING";

  return (
    <div className="max-w-2xl">
      <div className="flex items-center gap-2 text-sm text-slate-500 mb-4">
        <Link href="/pre-approvals" className="hover:text-brand-600 flex items-center gap-1">
          <ChevronLeft size={14} /> Pré-aprovações
        </Link>
        <span>/</span>
        <span className="text-slate-700">{req.product_label ?? `#${req.id}`}</span>
      </div>

      <PageHeader
        title={req.product_label ?? `Solicitação #${req.id}`}
        subtitle={req.operation_type}
        action={
          canDecide && !isTerminal(req.status) && !showDecision ? (
            <button onClick={() => {
              decisionForm.reset({
                status: req.status === "PENDING" ? "IN_REVIEW" : "APPROVED",
                compliance_opinion: "",
              });
              setShowDecision(true);
            }} className="btn-primary text-sm">
              Atualizar status
            </button>
          ) : canEmployeeCancel ? (
            <button onClick={() => decisionMutation.mutate({ status: "CANCELLED" })} className="btn-ghost text-sm">
              Cancelar solicitação
            </button>
          ) : undefined
        }
      />

      <Timeline request={req} />

      {/* badge status */}
      <div className="flex items-center gap-2 mb-6">
        <span className={`text-sm font-medium px-3 py-1 rounded-full ${cfg.badge}`}>{cfg.label}</span>
        {req.reviewer && (
          <span className="text-xs text-slate-500">por {req.reviewer}</span>
        )}
        {req.decided_at && (
          <span className="text-xs text-slate-400">em {fmtDate(req.decided_at)}</span>
        )}
      </div>

      {actionError && <Alert variant="error" className="mb-4">{actionError}</Alert>}

      {/* form decisão */}
      {showDecision && (
        <div className="card p-5 mb-5 border-2 border-brand-200">
          <h3 className="text-sm font-semibold text-slate-800 mb-4">Registrar decisão</h3>
          <form onSubmit={decisionForm.handleSubmit((d) => { setActionError(""); decisionMutation.mutate(d); })}
            className="space-y-3">
            <div>
              <label className="label">Status</label>
              <select {...decisionForm.register("status")} className="input">
                {statusOptions.map((status) => (
                  <option key={status} value={status}>{STATUS_CONFIG[status as StatusKey].label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="label">Parecer do compliance</label>
              <textarea {...decisionForm.register("compliance_opinion")} rows={3}
                className="input resize-none" placeholder="Fundamento da decisão, condições ou restrições…" />
              {decisionForm.formState.errors.compliance_opinion && (
                <p className="text-xs text-red-600 mt-1">{decisionForm.formState.errors.compliance_opinion.message}</p>
              )}
            </div>
            <div className="flex justify-end gap-3">
              <button type="button" onClick={() => setShowDecision(false)} className="btn-ghost text-sm">Cancelar</button>
              <button type="submit" disabled={decisionMutation.isPending}
                className="btn-primary text-sm flex items-center gap-2">
                {decisionMutation.isPending && <Spinner className="h-4 w-4 border-white border-t-transparent" />}
                Confirmar decisão
              </button>
            </div>
          </form>
        </div>
      )}

      {/* dados da solicitação */}
      <div className="card p-5 mb-5">
        <h3 className="text-sm font-semibold text-slate-700 mb-3">Dados da solicitação</h3>
        <div className="space-y-2 text-sm">
          {req.estimated_amount && (
            <div className="flex gap-2">
              <span className="w-36 text-xs text-slate-500">Valor estimado</span>
              <span>{fmtCurrency(req.estimated_amount)}</span>
            </div>
          )}
          {req.intended_date && (
            <div className="flex gap-2">
              <span className="w-36 text-xs text-slate-500">Data pretendida</span>
              <span>{fmtDate(req.intended_date)}</span>
            </div>
          )}
          <div className="flex gap-2">
            <span className="w-36 text-xs text-slate-500">Solicitado em</span>
            <span>{fmtDateTime(req.created_at)}</span>
          </div>
          {req.justification && (
            <div className="pt-2 border-t border-slate-100 mt-2">
              <p className="text-xs text-slate-500 mb-1">Justificativa</p>
              <p className="text-slate-700 whitespace-pre-wrap">{req.justification}</p>
            </div>
          )}
        </div>
      </div>

      {/* resposta inicial do copilot */}
      {req.copilot_initial_response && (
        <div className="card p-5 mb-5 bg-blue-50 border-blue-100">
          <div className="flex items-center justify-between gap-2 mb-2">
            <p className="text-xs font-semibold text-blue-700">Análise inicial do Copilot</p>
            {req.source_query_id && <Link href={`/history/${req.source_query_id}`} className="text-xs text-brand-600 hover:underline">Consulta #{req.source_query_id}</Link>}
          </div>
          {req.copilot_initial_decision && <p className="text-xs font-medium text-blue-700 mb-2">Decisão inicial: {req.copilot_initial_decision}</p>}
          <p className="text-xs text-blue-800 whitespace-pre-wrap">{req.copilot_initial_response}</p>
        </div>
      )}

      {/* parecer compliance */}
      {req.compliance_opinion && (
        <div className="card p-5 mb-5">
          <p className="text-xs font-semibold text-slate-700 mb-2">Parecer do compliance</p>
          <p className="text-sm text-slate-700 whitespace-pre-wrap">{req.compliance_opinion}</p>
        </div>
      )}

      {/* comentários */}
      <div className="card mb-5">
        <div className="px-5 py-4 border-b border-slate-100">
          <h3 className="text-sm font-semibold text-slate-700">
            Comentários
            {req.comments?.length > 0 && (
              <span className="ml-2 text-xs font-normal text-slate-400">{req.comments.length}</span>
            )}
          </h3>
        </div>
        <div className="divide-y divide-slate-50">
          {(req.comments ?? []).map((c: any) => (
            <div key={c.id} className="px-5 py-3">
              <div className="flex items-center gap-2 mb-1">
                <span className="text-xs font-medium text-slate-700">{c.author_name}</span>
                <span className="text-xs text-slate-400">{fmtDateTime(c.created_at)}</span>
              </div>
              <p className="text-sm text-slate-600">{c.body}</p>
            </div>
          ))}
          {(req.comments ?? []).length === 0 && (
            <p className="px-5 py-6 text-sm text-slate-400 text-center">Sem comentários ainda.</p>
          )}
        </div>
        {canComment && <div className="px-5 py-4 border-t border-slate-100">
          <form onSubmit={commentForm.handleSubmit((d) => commentMutation.mutate(d))}
            className="flex gap-2">
            <input {...commentForm.register("body")} className="input flex-1 text-sm"
              placeholder="Adicionar comentário…" />
            <button type="submit" disabled={commentMutation.isPending}
              className="btn-primary text-sm px-3 flex items-center gap-1">
              {commentMutation.isPending
                ? <Spinner className="h-4 w-4 border-white border-t-transparent" />
                : <Send size={14} />}
            </button>
          </form>
        </div>}
      </div>
    </div>
  );
}
