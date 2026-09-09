"use client";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { PageHeader } from "@/components/layout/PageHeader";
import { DecisionBadge } from "@/components/ui/DecisionBadge";
import { RiskBadge } from "@/components/ui/RiskBadge";
import { Spinner } from "@/components/ui/Spinner";
import { EmptyState } from "@/components/ui/EmptyState";
import { Alert } from "@/components/ui/Alert";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { VersionBadge } from "@/components/ui/VersionBadge";
import { Scale, X, FlaskConical } from "lucide-react";

// ─── constantes ────────────────────────────────────────────────────────────────

const DECISIONS = [
  "ALLOWED",
  "REPORT_REQUIRED",
  "PRE_APPROVAL_REQUIRED",
  "RESTRICTED",
  "INCONCLUSIVE",
] as const;

const RISKS = ["LOW", "MEDIUM", "HIGH"] as const;

const PRODUCT_TYPES = [
  "OPEN_FUND",
  "CLOSED_FUND",
  "EXCLUSIVE_FUND",
  "STOCK",
  "DERIVATIVE",
  "CRYPTO",
  "IPO",
  "FIXED_INCOME",
  "OTHER",
];

const DECISION_LABELS: Record<string, string> = {
  ALLOWED: "Permitido",
  REPORT_REQUIRED: "Requer Reporte",
  PRE_APPROVAL_REQUIRED: "Requer Pré-aprovação",
  RESTRICTED: "Restrito",
  INCONCLUSIVE: "Inconclusivo",
};

const RISK_LABELS: Record<string, string> = {
  LOW: "Baixo",
  MEDIUM: "Médio",
  HIGH: "Alto",
};

// ─── schemas ───────────────────────────────────────────────────────────────────

const ruleSchema = z.object({
  rule_key: z.string().regex(/^[a-z0-9]+(?:-[a-z0-9]+)*$/, "Use letras minúsculas, números e hífens").optional().or(z.literal("")),
  name: z.string().min(3, "Mínimo 3 caracteres"),
  description: z.string().optional(),
  product_type: z.string().optional(),
  decision: z.enum(DECISIONS),
  risk: z.enum(RISKS),
  priority: z.coerce.number().int().min(1).max(999),
  status: z.enum(["DRAFT", "ACTIVE", "ARCHIVED"]),
  effective_from: z.string().optional(),
  effective_to: z.string().optional(),
  condition_amount_gt: z.coerce.number().min(0).optional().or(z.literal("")),
});
type RuleForm = z.infer<typeof ruleSchema>;

const simulateSchema = z.object({
  product_type: z.string().optional(),
  amount: z.coerce.number().min(0).optional().or(z.literal("")),
});
type SimForm = z.infer<typeof simulateSchema>;

// ─── helpers ───────────────────────────────────────────────────────────────────

function buildCondition(form: RuleForm): Record<string, unknown> {
  if (form.condition_amount_gt && Number(form.condition_amount_gt) > 0) {
    return { amount_gt: Number(form.condition_amount_gt) };
  }
  return {};
}

function formFromRule(r: any): RuleForm {
  return {
    name: r.name,
    rule_key: r.rule_key,
    description: r.description ?? "",
    product_type: r.product_type ?? "",
    decision: r.decision,
    risk: r.risk,
    priority: r.priority,
    status: r.status,
    effective_from: r.status === "DRAFT" ? r.effective_from?.slice(0, 16) ?? "" : "",
    effective_to: r.status === "DRAFT" ? r.effective_to?.slice(0, 16) ?? "" : "",
    condition_amount_gt: r.condition?.amount_gt ?? "",
  };
}

// ─── componentes auxiliares ────────────────────────────────────────────────────

function Modal({
  title,
  onClose,
  children,
  wide,
}: {
  title: string;
  onClose: () => void;
  children: React.ReactNode;
  wide?: boolean;
}) {
  return (
    <div className="modal-backdrop">
      <div className={`modal-panel ${wide ? "max-w-2xl" : "max-w-lg"}`} role="dialog" aria-modal="true" aria-labelledby="rule-modal-title">
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100">
          <h2 id="rule-modal-title" className="font-semibold text-slate-950">{title}</h2>
          <button onClick={onClose} className="rounded-md p-1.5 text-slate-500 hover:bg-slate-100" aria-label="Fechar">
            <X size={18} />
          </button>
        </div>
        <div className="px-6 py-5">{children}</div>
      </div>
    </div>
  );
}

function Field({
  label,
  error,
  hint,
  children,
}: {
  label: string;
  error?: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <label className="block">
      <span className="label">{label}</span>
      {children}
      {hint && !error && <p className="text-xs text-slate-400 mt-1">{hint}</p>}
      {error && <p className="text-xs text-red-600 mt-1">{error}</p>}
    </label>
  );
}

// ─── formulário de regra (criar / editar) ──────────────────────────────────────

function RuleFormBody({
  form,
  onSubmit,
  onCancel,
  isPending,
  error,
  submitLabel,
}: {
  form: ReturnType<typeof useForm<RuleForm>>;
  onSubmit: (d: RuleForm) => void;
  onCancel: () => void;
  isPending: boolean;
  error: string;
  submitLabel: string;
}) {
  const { register, handleSubmit, formState: { errors } } = form;

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">
      {error && <Alert variant="error">{error}</Alert>}

      <Field label="Nome da regra" error={errors.name?.message}>
        <input {...register("name")} className="input" placeholder="Ex: Fundos abertos acima de R$ 100k" />
      </Field>

      <Field label="Chave estável" error={errors.rule_key?.message} hint="Identifica todas as versões da mesma regra">
        <input {...register("rule_key")} className="input font-mono" placeholder="ex: fundos-acima-100k" />
      </Field>

      <Field label="Descrição" error={errors.description?.message}>
        <textarea {...register("description")} rows={2} className="input resize-none"
          placeholder="Contexto e motivação da regra" />
      </Field>

      <div className="grid grid-cols-2 gap-4">
        <Field label="Tipo de produto" hint="Vazio = aplica a todos">
          <select {...register("product_type")} className="input">
            <option value="">Todos os tipos</option>
            {PRODUCT_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
          </select>
        </Field>
        <Field label="Condição: valor maior que (R$)" hint="0 = sem condição de valor">
          <input {...register("condition_amount_gt")} type="number" min={0} step={1000}
            className="input" placeholder="0" />
        </Field>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <Field label="Decisão" error={errors.decision?.message}>
          <select {...register("decision")} className="input">
            {DECISIONS.map((d) => <option key={d} value={d}>{DECISION_LABELS[d]}</option>)}
          </select>
        </Field>
        <Field label="Risco" error={errors.risk?.message}>
          <select {...register("risk")} className="input">
            {RISKS.map((r) => <option key={r} value={r}>{RISK_LABELS[r]}</option>)}
          </select>
        </Field>
        <Field label="Prioridade" error={errors.priority?.message} hint="Menor = avaliada primeiro">
          <input {...register("priority")} type="number" min={1} max={999} className="input" />
        </Field>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <Field label="Vigência inicial"><input {...register("effective_from")} type="datetime-local" className="input" /></Field>
        <Field label="Vigência final" hint="Opcional"><input {...register("effective_to")} type="datetime-local" className="input" /></Field>
      </div>

      <div className="flex justify-end gap-3 pt-2 border-t border-slate-100">
        <button type="button" onClick={onCancel} className="btn-ghost text-sm">Cancelar</button>
        <button type="submit" disabled={isPending} className="btn-primary text-sm flex items-center gap-2">
          {isPending && <Spinner className="h-4 w-4 border-white border-t-transparent" />}
          {submitLabel}
        </button>
      </div>
    </form>
  );
}

// ─── página principal ──────────────────────────────────────────────────────────

export default function RulesPage() {
  const { user } = useAuth();
  const qc = useQueryClient();
  const canEdit = user && ["ADMIN", "COMPLIANCE"].includes(user.role);

  const [showCreate, setShowCreate] = useState(false);
  const [editing, setEditing] = useState<any>(null);
  const [simulating, setSimulating] = useState(false);
  const [simResult, setSimResult] = useState<any>(null);
  const [error, setError] = useState("");
  const [deleteTarget, setDeleteTarget] = useState<any>(null);

  const { data: rules = [], isLoading } = useQuery({
    queryKey: ["rules"],
    queryFn: () => api.get("/rules").then((r) => r.data),
  });

  const createForm = useForm<RuleForm>({
    resolver: zodResolver(ruleSchema),
    defaultValues: { decision: "ALLOWED", risk: "MEDIUM", priority: 100, status: "DRAFT" },
  });

  const editForm = useForm<RuleForm>({ resolver: zodResolver(ruleSchema) });

  const simForm = useForm<SimForm>({ resolver: zodResolver(simulateSchema) });

  // mutations
  const createMutation = useMutation({
    mutationFn: (d: RuleForm) =>
      api.post("/rules", { ...d, rule_key: d.rule_key || null, product_type: d.product_type || null, effective_from: d.effective_from || null, effective_to: d.effective_to || null, condition: buildCondition(d) }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["rules"] }); setShowCreate(false); createForm.reset(); },
    onError: (e: any) => setError(e.response?.data?.detail ?? "Erro ao criar regra"),
  });

  const editMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: RuleForm }) =>
      api.patch(`/rules/${id}`, { ...data, product_type: data.product_type || null, effective_from: data.effective_from || null, effective_to: data.effective_to || null, condition: buildCondition(data) }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["rules"] }); setEditing(null); },
    onError: (e: any) => setError(e.response?.data?.detail ?? "Erro ao salvar regra"),
  });

  const activateMutation = useMutation({
    mutationFn: (id: number) => api.post(`/rules/${id}/activate`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["rules"] }),
    onError: (e: any) => setError(e.response?.data?.detail ?? "Erro ao ativar regra"),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.delete(`/rules/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["rules"] }),
  });

  const simMutation = useMutation({
    mutationFn: (d: SimForm) =>
      api.post("/rules/evaluate", {
        product_type: d.product_type || null,
        amount: d.amount ? Number(d.amount) : null,
      }).then((r) => r.data),
    onSuccess: (data) => setSimResult(data),
    onError: (e: any) => setError(e.response?.data?.detail ?? "Erro na simulação"),
  });

  const openEdit = (r: any) => {
    setEditing(r);
    setError("");
    editForm.reset(formFromRule(r));
  };

  const active = rules.filter((r: any) => r.status === "ACTIVE").length;

  return (
    <div>
      <PageHeader
        title="Regras de Compliance"
        subtitle={`${rules.length} regras · ${active} ativas`}
        action={
          canEdit ? (
            <div className="flex gap-2">
              <button onClick={() => { setSimulating(true); setSimResult(null); setError(""); }}
                className="btn-ghost text-sm flex items-center gap-2 border border-slate-200">
                <FlaskConical size={14} /> Simular
              </button>
              <button onClick={() => { setShowCreate(true); setError(""); }}
                className="btn-primary text-sm">
                + Nova regra
              </button>
            </div>
          ) : (
            <button onClick={() => { setSimulating(true); setSimResult(null); setError(""); }}
              className="btn-ghost text-sm flex items-center gap-2 border border-slate-200">
              <FlaskConical size={14} /> Simular
            </button>
          )
        }
      />

      {error && !showCreate && !editing && <Alert variant="error" className="mb-4">{error}</Alert>}

      {isLoading ? (
        <div className="flex justify-center py-16"><Spinner className="h-8 w-8" /></div>
      ) : rules.length === 0 ? (
        <EmptyState message="Nenhuma regra configurada." icon={<Scale />} />
      ) : (
        <div className="card overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-xs text-slate-500 uppercase tracking-wide">
              <tr>
                <th className="px-4 py-3 text-left">Nome</th>
                <th className="px-4 py-3 text-left">Versão</th>
                <th className="px-4 py-3 text-left">Vigência</th>
                <th className="px-4 py-3 text-left">Condição</th>
                <th className="px-4 py-3 text-left">Decisão</th>
                <th className="px-4 py-3 text-left">Risco</th>
                <th className="px-4 py-3 text-right">Prioridade</th>
                <th className="px-4 py-3 text-left">Status</th>
                {canEdit && <th className="px-4 py-3 text-right">Ações</th>}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {rules.map((r: any) => (
                <tr key={r.id} className={`transition-colors ${r.status === "ARCHIVED" ? "bg-slate-50 text-slate-500" : "hover:bg-slate-50"}`}>
                  <td className="px-4 py-3">
                    <p className="font-medium text-slate-800">{r.name}</p>
                    <p className="mt-0.5 font-mono text-[11px] text-slate-500">{r.rule_key}</p>
                    {r.description && <p className="text-xs text-slate-400 mt-0.5 line-clamp-1">{r.description}</p>}
                  </td>
                  <td className="px-4 py-3"><VersionBadge version={r.version} status={r.status} /></td>
                  <td className="px-4 py-3 whitespace-nowrap text-xs text-slate-500">{new Date(r.effective_from).toLocaleDateString("pt-BR")}{r.effective_to ? ` — ${new Date(r.effective_to).toLocaleDateString("pt-BR")}` : " — aberta"}</td>
                  <td className="px-4 py-3 text-slate-500 text-xs">
                    {r.condition?.amount_gt
                      ? `> R$ ${Number(r.condition.amount_gt).toLocaleString("pt-BR")}`
                      : "—"}
                  </td>
                  <td className="px-4 py-3"><DecisionBadge decision={r.decision} /></td>
                  <td className="px-4 py-3"><RiskBadge risk={r.risk} /></td>
                  <td className="px-4 py-3 text-right text-slate-500 tabular-nums">{r.priority}</td>
                  <td className="px-4 py-3">
                    <span className="text-xs font-semibold text-slate-600">{r.status}</span>
                  </td>
                  {canEdit && (
                    <td className="px-4 py-3 text-right">
                      <div className="flex justify-end gap-3">
                        <button onClick={() => openEdit(r)}
                          className="text-xs text-brand-600 hover:underline">
                          Editar
                        </button>
                        {r.status === "DRAFT" && <button onClick={() => activateMutation.mutate(r.id)} className="text-xs font-semibold text-emerald-700 hover:underline">Ativar</button>}
                        {r.status === "DRAFT" && <button
                          onClick={() => setDeleteTarget(r)}
                          className="text-xs text-red-500 hover:underline">
                          Excluir
                        </button>}
                      </div>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* modal: criar */}
      {showCreate && (
        <Modal title="Nova regra" onClose={() => { setShowCreate(false); setError(""); }} wide>
          <RuleFormBody
            form={createForm}
            onSubmit={(d) => { setError(""); createMutation.mutate(d); }}
            onCancel={() => { setShowCreate(false); setError(""); }}
            isPending={createMutation.isPending}
            error={error}
            submitLabel="Criar regra"
          />
        </Modal>
      )}

      {/* modal: editar */}
      {editing && (
        <Modal title={editing.status === "DRAFT" ? `Editar rascunho — ${editing.name}` : `Criar nova versão — ${editing.name}`} onClose={() => { setEditing(null); setError(""); }} wide>
          {editing.status !== "DRAFT" && <Alert variant="info" className="mb-4">A versão publicada é imutável. Ao salvar, uma nova versão será criada e a anterior ficará arquivada.</Alert>}
          <RuleFormBody
            form={editForm}
            onSubmit={(d) => { setError(""); editMutation.mutate({ id: editing.id, data: d }); }}
            onCancel={() => { setEditing(null); setError(""); }}
            isPending={editMutation.isPending}
            error={error}
            submitLabel="Salvar alterações"
          />
        </Modal>
      )}

      {/* modal: simular */}
      {simulating && (
        <Modal title="Simular motor de regras" onClose={() => { setSimulating(false); setSimResult(null); setError(""); }}>
          <form onSubmit={simForm.handleSubmit((d) => { setError(""); simMutation.mutate(d); })}
            className="flex flex-col gap-4">
            {error && <Alert variant="error">{error}</Alert>}
            <p className="text-sm text-slate-500">
              Simule o resultado do motor para um tipo de produto e valor, sem salvar nada.
            </p>
            <div className="grid grid-cols-2 gap-4">
              <Field label="Tipo de produto">
                <select {...simForm.register("product_type")} className="input">
                  <option value="">Nenhum</option>
                  {PRODUCT_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
                </select>
              </Field>
              <Field label="Valor estimado (R$)">
                <input {...simForm.register("amount")} type="number" min={0} step={1000} className="input" placeholder="0" />
              </Field>
            </div>

            <div className="flex justify-end gap-3">
              <button type="button" onClick={() => { setSimulating(false); setSimResult(null); }} className="btn-ghost text-sm">
                Fechar
              </button>
              <button type="submit" disabled={simMutation.isPending}
                className="btn-primary text-sm flex items-center gap-2">
                {simMutation.isPending && <Spinner className="h-4 w-4 border-white border-t-transparent" />}
                Simular
              </button>
            </div>
          </form>

          {simResult && (
            <div className="mt-5 border-t border-slate-100 pt-5 space-y-3">
              <div className="flex items-center gap-3 flex-wrap">
                <DecisionBadge decision={simResult.decision} />
                <RiskBadge risk={simResult.risk_level} />
                {simResult.requires_human_review && (
                  <span className="text-xs font-medium bg-amber-100 text-amber-700 px-2 py-0.5 rounded-full">
                    Revisão humana
                  </span>
                )}
              </div>
              <div className="bg-slate-50 rounded-lg px-4 py-3 text-sm text-slate-600">
                <span className="font-medium text-slate-700">Motivo: </span>{simResult.reason}
              </div>
              {simResult.matched_rules?.length > 0 && (
                <div>
                  <p className="text-xs text-slate-500 mb-1">Regras aplicadas</p>
                  <div className="flex flex-wrap gap-1">
                    {simResult.matched_rules.map((name: string) => (
                      <span key={name} className="text-xs bg-brand-50 text-brand-700 px-2 py-0.5 rounded-full font-mono">
                        {name}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </Modal>
      )}

      <ConfirmDialog
        open={Boolean(deleteTarget)}
        title="Excluir regra de compliance"
        description={`A regra “${deleteTarget?.name ?? ""}” será removida do motor configurado. Esta ação não pode ser desfeita.`}
        confirmLabel="Excluir regra"
        destructive
        busy={deleteMutation.isPending}
        onClose={() => setDeleteTarget(null)}
        onConfirm={() => deleteTarget && deleteMutation.mutate(deleteTarget.id)}
      />
    </div>
  );
}
