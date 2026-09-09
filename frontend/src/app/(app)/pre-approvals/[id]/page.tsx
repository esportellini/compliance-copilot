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
import { StatusBadge } from "@/components/ui/StatusBadge";
import { DecisionBadge } from "@/components/ui/DecisionBadge";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { SlaBadge } from "@/components/ui/SlaBadge";
import { ExportMenu } from "@/components/ExportMenu";
import { STATUS_CONFIG, type StatusKey } from "@/lib/pre-approvals";
import { fmtCurrency, fmtDate, fmtDateTime } from "@/lib/utils";
import { Bot, CheckCircle2, ChevronLeft, MessageSquareText, Send, UserCheck } from "lucide-react";

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

function cleanCopilotSnapshot(value: string) {
  return value.replace(/\*\*/g, "").replace(/⚠️\s*/g, "").trim();
}

// ─── timeline ─────────────────────────────────────────────────────────────────
function Timeline({ request }: { request: any }) {
  const events = [
    { key: "created", label: "Solicitação criada", at: request.created_at, type: "human" },
    ...(request.copilot_initial_response ? [{ key: "analysis", label: `Análise inicial: ${request.copilot_initial_decision ?? "registrada"}`, at: request.created_at, type: "automated" }] : []),
    ...(request.review_started_at ? [{ key: "review", label: "Revisão humana iniciada", at: request.review_started_at, type: "review" }] : []),
    ...(request.comments ?? []).map((comment: any) => ({ key: `comment-${comment.id}`, label: `Comentário de ${comment.author_name}`, at: comment.created_at, type: "comment" })),
    ...(request.decided_at ? [{ key: "decision", label: `Decisão final: ${(STATUS_CONFIG[request.status as StatusKey] ?? STATUS_CONFIG.PENDING).label}`, at: request.decided_at, type: "decision" }] : []),
    ...(request.status === "CANCELLED" ? [{ key: "cancelled", label: "Solicitação cancelada", at: request.updated_at, type: "decision" }] : []),
  ].sort((a, b) => new Date(a.at).getTime() - new Date(b.at).getTime());
  return (
    <div className="card mb-6 p-5">
      <h3 className="text-sm font-semibold text-slate-900">Linha do tempo</h3>
      <div className="mt-4">
        {events.map((event, index) => {
          const Icon = event.type === "automated" ? Bot : event.type === "comment" ? MessageSquareText : event.type === "review" ? UserCheck : CheckCircle2;
          return <div key={event.key} className="relative flex gap-3 pb-5 last:pb-0">{index < events.length - 1 && <span className="absolute left-[11px] top-6 h-[calc(100%-18px)] w-px bg-slate-200" aria-hidden="true" />}<span className={`relative z-10 flex h-6 w-6 shrink-0 items-center justify-center rounded-full ring-4 ring-white ${event.type === "automated" ? "bg-blue-100 text-blue-700" : "bg-brand-100 text-brand-800"}`}><Icon size={13} /></span><div><p className="text-sm font-medium text-slate-800">{event.label}</p><p className="mt-0.5 text-xs tabular-nums text-slate-500">{fmtDateTime(event.at)}</p>{event.type === "automated" && <p className="mt-1 text-[10px] font-semibold uppercase tracking-[0.08em] text-blue-600">Análise automatizada</p>}</div></div>;
        })}
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
  const [pendingDecision, setPendingDecision] = useState<DecisionForm | null>(null);

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
    onSuccess: () => { invalidate(); setShowDecision(false); setPendingDecision(null); setActionError(""); },
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
    <div className="max-w-5xl">
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
            <button onClick={() => setPendingDecision({ status: "CANCELLED" })} className="btn-secondary text-red-700 hover:border-red-300 hover:bg-red-50">
              Cancelar solicitação
            </button>
          ) : undefined
        }
      />

      <div className="mb-5 flex justify-end"><ExportMenu requestId={id} /></div>

      <Timeline request={req} />

      {/* badge status */}
      <div className="mb-6 flex flex-wrap items-center gap-2 rounded-lg border border-slate-200 bg-white px-4 py-3">
        <StatusBadge status={req.status} label={cfg.label} />
        <SlaBadge status={req.sla_status} />
        {req.due_at && <span className="text-xs text-slate-500">prazo {fmtDateTime(req.due_at)}</span>}
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
          <form onSubmit={decisionForm.handleSubmit((d) => { setActionError(""); setPendingDecision(d); })}
            className="space-y-3">
            <div>
              <label htmlFor="approval-status" className="label">Status</label>
              <select id="approval-status" {...decisionForm.register("status")} className="input">
                {statusOptions.map((status) => (
                  <option key={status} value={status}>{STATUS_CONFIG[status as StatusKey].label}</option>
                ))}
              </select>
            </div>
            <div>
              <label htmlFor="compliance-opinion" className="label">Parecer do compliance</label>
              <textarea id="compliance-opinion" {...decisionForm.register("compliance_opinion")} rows={3}
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
          {req.copilot_initial_decision && <div className="mb-3"><DecisionBadge decision={req.copilot_initial_decision} /></div>}
          <p className="text-xs leading-6 text-blue-900 whitespace-pre-wrap">{cleanCopilotSnapshot(req.copilot_initial_response)}</p>
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
              className="btn-primary text-sm px-3 flex items-center gap-1" aria-label="Enviar comentário">
              {commentMutation.isPending
                ? <Spinner className="h-4 w-4 border-white border-t-transparent" />
                : <Send size={14} />}
            </button>
          </form>
        </div>}
      </div>
      <ConfirmDialog
        open={pendingDecision !== null}
        title={pendingDecision?.status === "CANCELLED" ? "Cancelar solicitação" : "Confirmar atualização de status"}
        description={pendingDecision?.status === "CANCELLED" ? "O cancelamento é terminal e não poderá ser revertido." : "Esta ação será registrada na trilha de auditoria. Revise o status e o parecer antes de confirmar."}
        confirmLabel={pendingDecision?.status === "CANCELLED" ? "Cancelar solicitação" : "Registrar decisão"}
        destructive={pendingDecision?.status === "CANCELLED" || pendingDecision?.status === "REJECTED"}
        busy={decisionMutation.isPending}
        onClose={() => setPendingDecision(null)}
        onConfirm={() => pendingDecision && decisionMutation.mutate(pendingDecision)}
      />
    </div>
  );
}
