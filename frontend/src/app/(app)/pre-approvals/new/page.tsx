"use client";
import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter, useSearchParams } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import Link from "next/link";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { PageHeader } from "@/components/layout/PageHeader";
import { Alert } from "@/components/ui/Alert";
import { Spinner } from "@/components/ui/Spinner";
import { DecisionBadge } from "@/components/ui/DecisionBadge";
import { OPERATION_TYPES } from "@/lib/pre-approvals";
import { ArrowLeft, Link2 } from "lucide-react";

const schema = z.object({
  product_label:    z.string().min(2, "Informe o produto"),
  operation_type:   z.string().min(1, "Selecione a operação"),
  estimated_amount: z.coerce.number().min(0).optional().or(z.literal("")),
  intended_date:    z.string().optional(),
  justification:    z.string().optional(),
});
type Form = z.infer<typeof schema>;

function Field({ label, hint, error, children }: {
  label: string; hint?: string; error?: string; children: React.ReactNode;
}) {
  return (
    <label className="block">
      <span className="label">{label}</span>
      {children}
      {hint && !error && <p className="field-help">{hint}</p>}
      {error && <p className="field-error">{error}</p>}
    </label>
  );
}

export default function NewPreApprovalPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const qc = useQueryClient();
  const { user } = useAuth();
  const [error, setError] = useState("");
  const fromQuery = searchParams.get("from_query");
  const sourceQueryId = fromQuery && /^\d+$/.test(fromQuery) ? Number(fromQuery) : null;

  const { register, handleSubmit, reset, formState: { errors } } = useForm<Form>({
    resolver: zodResolver(schema),
  });

  const sourceQuery = useQuery({
    queryKey: ["history-detail", sourceQueryId],
    queryFn: () => api.get(`/copilot/history/${sourceQueryId}`).then((r) => r.data),
    enabled: sourceQueryId !== null,
    retry: false,
  });

  useEffect(() => {
    if (!sourceQuery.data) return;
    reset({
      product_label: sourceQuery.data.product_label ?? sourceQuery.data.product_identifier ?? "",
      operation_type: "",
      estimated_amount: sourceQuery.data.amount ?? "",
      justification: sourceQuery.data.objective ?? "",
    });
  }, [reset, sourceQuery.data]);

  const mutation = useMutation({
    mutationFn: (d: Form) => {
      const payload: any = {
        product_label: d.product_label,
        operation_type: d.operation_type,
      };
      if (sourceQueryId !== null) payload.source_query_id = sourceQueryId;
      if (sourceQuery.data?.product_id) payload.product_id = sourceQuery.data.product_id;
      if (d.estimated_amount) payload.estimated_amount = Number(d.estimated_amount);
      if (d.intended_date) payload.intended_date = d.intended_date;
      if (d.justification) payload.justification = d.justification;
      return api.post("/pre-approvals", payload);
    },
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: ["pre-approvals"] });
      router.push(`/pre-approvals/${res.data.id}`);
    },
    onError: (e: any) => setError(e.response?.data?.detail ?? "Erro ao criar solicitação"),
  });

  if (user?.role === "AUDITOR") {
    return <Alert variant="info">Auditores possuem acesso somente leitura.</Alert>;
  }

  return (
    <div className="max-w-4xl">
      <Link href="/pre-approvals" className="mb-5 inline-flex items-center gap-1.5 text-sm font-semibold text-slate-500 hover:text-brand-700"><ArrowLeft size={15} />Voltar para a fila</Link>

      <PageHeader title="Nova pré-aprovação" subtitle="Registre a operação e preserve o vínculo com a análise inicial, quando disponível." />

      {fromQuery && sourceQuery.data && <section className="mb-5 rounded-lg border border-blue-200 bg-blue-50 p-4"><div className="flex flex-wrap items-center gap-3"><span className="flex h-8 w-8 items-center justify-center rounded-md bg-blue-100 text-blue-800"><Link2 size={16} /></span><div className="min-w-0 flex-1"><p className="text-xs font-semibold uppercase tracking-[0.08em] text-blue-700">Origem: consulta Copilot #{fromQuery}</p><p className="mt-1 truncate text-sm font-medium text-blue-950">{sourceQuery.data.product_label ?? sourceQuery.data.product_identifier ?? "Produto não identificado"}</p></div>{sourceQuery.data.answer?.decision && <DecisionBadge decision={sourceQuery.data.answer.decision} />}</div><p className="mt-3 text-xs leading-5 text-blue-800">A análise estruturada já persistida será reutilizada. Revise os campos herdados e informe manualmente o tipo de operação.</p></section>}

      {fromQuery && !sourceQueryId && (
        <Alert variant="error" className="mb-4">Identificador de consulta inválido.</Alert>
      )}
      {sourceQuery.isLoading && (
        <Alert variant="info" className="mb-4">Carregando contexto da consulta…</Alert>
      )}
      {sourceQuery.error && (
        <Alert variant="error" className="mb-4">
          {(sourceQuery.error as any).response?.data?.detail ?? "Não foi possível carregar a consulta vinculada."}
        </Alert>
      )}

      <div className="card p-5 sm:p-6">
        <form onSubmit={handleSubmit((d) => { setError(""); mutation.mutate(d); })} className="space-y-5">
          {error && <Alert variant="error">{error}</Alert>}

          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Produto *" error={errors.product_label?.message}>
              <input {...register("product_label")} readOnly={sourceQueryId !== null}
                className="input read-only:bg-slate-50" placeholder="Ex: Fundo Alpha ou XPTO3" />
            </Field>
            <Field label="Tipo de operação *" error={errors.operation_type?.message}>
              <select {...register("operation_type")} className="input">
                <option value="">Selecionar…</option>
                {OPERATION_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
              </select>
            </Field>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Valor estimado (R$)">
              <input {...register("estimated_amount")} readOnly={sourceQueryId !== null}
                type="number" min={0} step={1000} className="input read-only:bg-slate-50" placeholder="0" />
            </Field>
            <Field label="Data pretendida">
              <input {...register("intended_date")} type="date" className="input" />
            </Field>
          </div>

          <Field label="Justificativa" hint="Descreva o objetivo e motivação da operação">
            <textarea {...register("justification")} rows={4} className="input resize-none"
              placeholder="Ex: Diversificação da carteira pessoal com exposição a renda variável…" />
          </Field>

          <div className="flex flex-col-reverse justify-end gap-3 border-t border-slate-200 pt-5 sm:flex-row">
            <Link href="/pre-approvals" className="btn-secondary">Cancelar</Link>
            <button type="submit" disabled={mutation.isPending || sourceQuery.isLoading || !!sourceQuery.error || (!!fromQuery && !sourceQueryId)} className="btn-primary text-sm flex items-center gap-2">
              {mutation.isPending && <Spinner className="h-4 w-4 border-white border-t-transparent" />}
              Submeter solicitação
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
