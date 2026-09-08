"use client";
import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { Alert } from "@/components/ui/Alert";
import { Spinner } from "@/components/ui/Spinner";
import { PageHeader } from "@/components/layout/PageHeader";
import {
  DECISION_CONFIG, RISK_CONFIG, PRODUCT_TYPES, SUGGESTED_QUESTIONS,
  type DecisionKey,
} from "@/lib/copilot";
import { fmtCurrency } from "@/lib/utils";
import {
  Send, ChevronDown, ChevronUp, History, ClipboardCheck,
  UserCheck, AlertTriangle, Lightbulb,
} from "lucide-react";

const schema = z.object({
  question:          z.string().min(5, "Mínimo 5 caracteres"),
  product_type:      z.string().optional(),
  product_name_hint: z.string().optional(),
  amount:            z.coerce.number().min(0).optional().or(z.literal("")),
  objective:         z.string().optional(),
});
type Form = z.infer<typeof schema>;

// ─── card de resposta ─────────────────────────────────────────────────────────
function AnswerCard({ result, onOpenPreApproval }: { result: any; onOpenPreApproval: () => void }) {
  const [showSources, setShowSources] = useState(false);
  const [showRules, setShowRules] = useState(false);

  const decision = result.decision as DecisionKey;
  const cfg = DECISION_CONFIG[decision] ?? DECISION_CONFIG.INCONCLUSIVE;
  const riskCfg = RISK_CONFIG[result.risk_level as keyof typeof RISK_CONFIG] ?? RISK_CONFIG.MEDIUM;

  return (
    <div className={`card border-2 ${cfg.border} overflow-hidden`}>
      {/* cabeçalho da decisão */}
      <div className={`${cfg.bg} px-6 py-4 border-b ${cfg.border}`}>
        <div className="flex items-center gap-3 flex-wrap">
          <span className="text-2xl">{cfg.icon}</span>
          <div>
            <span className={`text-sm font-semibold px-3 py-1 rounded-full ${cfg.badge}`}>
              {cfg.label}
            </span>
          </div>
          <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${riskCfg.badge}`}>
            Risco {riskCfg.label}
          </span>
          {result.requires_human_review && (
            <span className="flex items-center gap-1 text-xs font-medium bg-amber-100 text-amber-700 px-2 py-0.5 rounded-full">
              <AlertTriangle size={11} /> Revisão humana
            </span>
          )}
          <span className="text-xs text-slate-400 ml-auto">
            Confiança {Math.round(result.confidence * 100)}%
          </span>
        </div>
      </div>

      <div className="px-6 py-5 space-y-4">
        {/* próxima ação */}
        {result.next_action && (
          <Alert
            variant={
              decision === "RESTRICTED" ? "error" :
              decision === "ALLOWED" ? "success" :
              decision === "PRE_APPROVAL_REQUIRED" ? "info" : "warning"
            }
            className="flex items-start gap-2"
          >
            <span className="font-semibold shrink-0">Próximo passo:</span>
            <span>{result.next_action}</span>
          </Alert>
        )}

        {/* fora de escopo */}
        {result.out_of_scope && (
          <Alert variant="warning">
            Esta pergunta está fora do escopo de compliance. Reformule especificando um produto ou operação.
          </Alert>
        )}

        {/* justificativa */}
        {!result.out_of_scope && (
          <div>
            <h3 className="text-sm font-semibold text-slate-700 mb-2">Justificativa</h3>
            <p className="text-sm text-slate-600 leading-relaxed">{result.justification}</p>
          </div>
        )}

        {/* aviso disclaimer */}
        <div className="bg-amber-50 border border-amber-200 rounded-lg px-4 py-3 text-xs text-amber-700 flex items-start gap-2">
          <AlertTriangle size={14} className="shrink-0 mt-0.5" />
          A resposta apoia a análise de compliance, mas não substitui revisão humana quando exigida pela política interna.
        </div>

        {/* regras aplicadas */}
        {result.matched_rules?.length > 0 && (
          <div>
            <button
              onClick={() => setShowRules(!showRules)}
              className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-700"
            >
              {showRules ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
              Regras aplicadas ({result.matched_rules.length})
            </button>
            {showRules && (
              <div className="mt-2 flex flex-wrap gap-1.5">
                {result.matched_rules.map((r: string) => (
                  <span key={r} className="text-xs bg-slate-100 text-slate-600 px-2 py-0.5 rounded font-mono">
                    {r}
                  </span>
                ))}
              </div>
            )}
          </div>
        )}

        {/* fontes */}
        {result.sources?.length > 0 && (
          <div>
            <button
              onClick={() => setShowSources(!showSources)}
              className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-700"
            >
              {showSources ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
              Fontes consultadas ({result.sources.length})
            </button>
            {showSources && (
              <div className="mt-3 space-y-2">
                {result.sources.map((s: any, i: number) => (
                  <div key={i} className="bg-slate-50 rounded-lg px-4 py-3 text-xs">
                    <p className="font-medium text-slate-700 mb-1">
                      {[s.document_name, s.section_title, s.page_number ? `pág. ${s.page_number}` : null]
                        .filter(Boolean).join(" · ")}
                    </p>
                    <p className="text-slate-500 line-clamp-3">{s.excerpt}</p>
                    <p className="text-slate-400 mt-1 text-right">
                      relevância {Math.round(s.score * 100)}%
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* ações pós-resposta */}
        <div className="flex flex-wrap gap-2 pt-2 border-t border-slate-100">
          {decision === "PRE_APPROVAL_REQUIRED" && (
            <button
              onClick={onOpenPreApproval}
              className="flex items-center gap-1.5 text-sm btn-primary"
            >
              <ClipboardCheck size={14} /> Abrir pré-aprovação
            </button>
          )}
          {result.requires_human_review && decision !== "PRE_APPROVAL_REQUIRED" && (
            <button
              onClick={onOpenPreApproval}
              className="flex items-center gap-1.5 text-sm border border-amber-300 text-amber-700 hover:bg-amber-50 px-3 py-2 rounded-lg transition-colors"
            >
              <UserCheck size={14} /> Solicitar revisão humana
            </button>
          )}
          {result.query_id && (
            <Link
              href={`/history/${result.query_id}`}
              className="flex items-center gap-1.5 text-sm text-slate-500 hover:text-brand-600 border border-slate-200 hover:border-brand-300 px-3 py-2 rounded-lg transition-colors"
            >
              <History size={14} /> Ver no histórico
            </Link>
          )}
        </div>
      </div>
    </div>
  );
}

// ─── página principal ─────────────────────────────────────────────────────────
export default function CopilotPage() {
  const router = useRouter();
  const { user } = useAuth();
  const [result, setResult]       = useState<any>(null);
  const [error, setError]         = useState("");
  const [showAdvanced, setAdv]    = useState(false);

  const { register, handleSubmit, setValue, formState: { errors, isSubmitting } } = useForm<Form>({
    resolver: zodResolver(schema),
  });

  const mutation = useMutation({
    mutationFn: async (data: Form) => {
      const payload: Record<string, unknown> = { question: data.question };
      if (data.product_type)      payload.product_type      = data.product_type;
      if (data.product_name_hint) payload.product_name_hint = data.product_name_hint;
      if (data.amount)            payload.amount             = Number(data.amount);
      if (data.objective)         payload.objective          = data.objective;
      return api.post("/copilot/query", payload).then((r) => r.data);
    },
    onSuccess: (data) => { setResult(data); setError(""); },
    onError: (e: any) => setError(e.response?.data?.detail ?? "Erro ao processar consulta."),
  });

  const onSubmit = (data: Form) => {
    setResult(null);
    mutation.mutate(data);
  };

  const openPreApproval = () => {
    if (result?.query_id) {
      router.push(`/pre-approvals/new?from_query=${result.query_id}`);
    } else {
      router.push("/pre-approvals/new");
    }
  };

  return (
    <div className="max-w-2xl">
      <PageHeader
        title="Compliance Copilot"
        subtitle="Tire dúvidas sobre operações e investimentos"
      />

      {/* aviso fixo */}
      <Alert variant="warning" className="mb-6 flex items-start gap-2">
        <AlertTriangle size={15} className="shrink-0 mt-0.5" />
        <span>
          As respostas apoiam a análise de compliance, mas não substituem revisão humana
          quando exigida pela política interna.
        </span>
      </Alert>

      {/* formulário */}
      {user?.role === "AUDITOR" ? (
        <Alert variant="info" className="mb-6">
          Auditores possuem acesso somente leitura. Consulte o histórico já registrado.
        </Alert>
      ) : <div className="card p-6 mb-6">
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          {/* pergunta principal */}
          <div>
            <label className="label">Sua pergunta *</label>
            <textarea
              {...register("question")}
              rows={3}
              className="input resize-none"
              placeholder="Ex: Posso comprar ações da XPTO3 com R$ 20.000?"
            />
            {errors.question && (
              <p className="text-xs text-red-600 mt-1">{errors.question.message}</p>
            )}
          </div>

          {/* campos opcionais */}
          <div>
            <button
              type="button"
              onClick={() => setAdv(!showAdvanced)}
              className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-700"
            >
              {showAdvanced ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
              {showAdvanced ? "Ocultar campos opcionais" : "Adicionar produto, valor ou objetivo"}
            </button>
          </div>

          {showAdvanced && (
            <div className="space-y-3 pt-1">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="label">Tipo de produto</label>
                  <select {...register("product_type")} className="input">
                    <option value="">Selecionar…</option>
                    {PRODUCT_TYPES.map(({ value, label }) => (
                      <option key={value} value={value}>{label}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="label">Produto (nome ou ticker)</label>
                  <input
                    {...register("product_name_hint")}
                    className="input"
                    placeholder="Ex: XPTO3 ou Fundo Alpha"
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="label">Valor estimado (R$)</label>
                  <input
                    {...register("amount")}
                    type="number" min={0} step={1000}
                    className="input" placeholder="0"
                  />
                </div>
                <div>
                  <label className="label">Objetivo</label>
                  <input
                    {...register("objective")}
                    className="input"
                    placeholder="Ex: diversificação"
                  />
                </div>
              </div>
            </div>
          )}

          {error && <Alert variant="error">{error}</Alert>}

          <button
            type="submit"
            disabled={mutation.isPending}
            className="btn-primary w-full flex items-center justify-center gap-2"
          >
            {mutation.isPending
              ? <><Spinner className="h-4 w-4 border-white border-t-transparent" /> Consultando…</>
              : <><Send size={14} /> Consultar</>}
          </button>
        </form>
      </div>}

      {/* resultado */}
      {result && (
        <div className="mb-8">
          <AnswerCard result={result} onOpenPreApproval={openPreApproval} />
        </div>
      )}

      {/* sugestões */}
      {!result && (
        <div>
          <div className="flex items-center gap-2 text-xs text-slate-500 mb-3">
            <Lightbulb size={13} />
            Sugestões de perguntas
          </div>
          <div className="flex flex-col gap-2">
            {SUGGESTED_QUESTIONS.map((q) => (
              <button
                key={q}
                onClick={() => { setValue("question", q); setAdv(false); }}
                className="text-left text-sm text-slate-600 hover:text-brand-600 bg-white border border-slate-200 hover:border-brand-300 px-4 py-3 rounded-lg transition-colors"
              >
                {q}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
