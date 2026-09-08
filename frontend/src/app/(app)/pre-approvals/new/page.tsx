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
import { OPERATION_TYPES } from "@/lib/pre-approvals";

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
    <div>
      <label className="label">{label}</label>
      {children}
      {hint && !error && <p className="text-xs text-slate-400 mt-1">{hint}</p>}
      {error && <p className="text-xs text-red-600 mt-1">{error}</p>}
    </div>
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
    <div className="max-w-xl">
      <div className="flex items-center gap-2 text-sm text-slate-500 mb-4">
        <Link href="/pre-approvals" className="hover:text-brand-600">Pré-aprovações</Link>
        <span>/</span>
        <span className="text-slate-700">Nova solicitação</span>
      </div>

      <PageHeader title="Nova pré-aprovação" subtitle="O Copilot fará uma análise inicial antes de submeter" />

      {fromQuery && (
        <Alert variant="info" className="mb-4">
          Pré-aprovação vinculada à consulta #{fromQuery}. A análise inicial persistida será reutilizada.
        </Alert>
      )}

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

      <div className="card p-6">
        <form onSubmit={handleSubmit((d) => { setError(""); mutation.mutate(d); })} className="space-y-4">
          {error && <Alert variant="error">{error}</Alert>}

          <div className="grid grid-cols-2 gap-4">
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

          <div className="grid grid-cols-2 gap-4">
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

          <div className="flex justify-end gap-3 pt-2">
            <Link href="/pre-approvals" className="btn-ghost text-sm">Cancelar</Link>
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
