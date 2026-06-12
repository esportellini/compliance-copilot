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
});
type DecisionForm = z.infer<typeof decisionSchema>;

const commentSchema = z.object({ body: z.string().min(1) });
type CommentForm = z.infer<typeof commentSchema>;

// ─── timeline ─────────────────────────────────────────────────────────────────
function Timeline({ status }: { status: string }) {
  const steps = [
    { key: "PENDING",   label: "Criada" },
    { key: "IN_REVIEW", label: "Em análise" },
    { key: "DONE",      label: "Encerrada" },
  ];
  const cfg = STATUS_CONFIG[status as StatusKey] ?? STATUS_CONFIG.PENDING;
  const step = cfg.step ?? 1;

  return (
    <div className="flex items-center gap-0 mb-6">
      {steps.map((s, i) => {
        const done   = i < step;
        const active = i === step - 1;
        return (
          <div key={s.key} className="flex items-center flex-1">
            <div className="flex flex-col items-center">
              <div className={`h-7 w-7 rounded-full flex items-center justify-center text-xs font-bold border-2
                ${done   ? "bg-brand-500 border-brand-500 text-white" :
                  active ? "bg-white border-brand-500 text-brand-600" :
                           "bg-white border-slate-300 text-slate-400"}`}>
                {i + 1}
              </div>
              <span className={`text-xs mt-1 ${active ? "text-brand-600 font-medium" : "text-slate-400"}`}>
                {s.label}
              </span>
            </div>
            {i < steps.length - 1 && (
              <div className={`flex-1 h-0.5 mx-2 ${done ? "bg-brand-400" : "bg-slate-200"}`} />
            )}
          </div>
        );
      })}
    </div>
  );
}

// ─── página ────────────────────────────────────────────────────────────────────
export default function PreApprovalDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();
  const qc = useQueryClient();
  const canDecide = user && ["ADMIN","COMPLIANCE"].includes(user.role);
  const isTerminal = (status: string) => TERMINAL.includes(status);

  const [showDecision, setShowDecision] = useState(false);
  const [actionError, setActionError] = useState("");

  const { data: req, isLoading } = useQuery({
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
  if (!req) return <Alert variant="error">Solicitação não encontrada.</Alert>;

  const cfg = STATUS_CONFIG[req.status as StatusKey] ?? STATUS_CONFIG.PENDING;

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
          canDecide && !isTerminal(req.status) && !showDecision && (
            <button onClick={() => setShowDecision(true)} className="btn-primary text-sm">
              Registrar decisão
            </button>
          )
        }
      />

      <Timeline status={req.status} />

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
                <option value="IN_REVIEW">Em análise</option>
                <option value="APPROVED">Aprovado</option>
                <option value="APPROVED_WITH_CONDITIONS">Aprovado com ressalvas</option>
                <option value="REJECTED">Rejeitado</option>
                <option value="CANCELLED">Cancelado</option>
              </select>
            </div>
            <div>
              <label className="label">Parecer do compliance</label>
              <textarea {...decisionForm.register("compliance_opinion")} rows={3}
                className="input resize-none" placeholder="Fundamento da decisão, condições ou restrições…" />
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
          <p className="text-xs font-semibold text-blue-700 mb-2">Análise inicial do Copilot</p>
          <p className="text-xs text-blue-800 whitespace-pre-wrap line-clamp-6">{req.copilot_initial_response}</p>
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
        <div className="px-5 py-4 border-t border-slate-100">
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
        </div>
      </div>
    </div>
  );
}