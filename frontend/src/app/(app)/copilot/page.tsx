"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMutation } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import {
  ArrowRight, BookOpenText, ChevronDown, ChevronUp, ClipboardCheck,
  FileCheck2, History, Info, ListChecks, MessageSquareText, Search,
  Send, ShieldCheck, UserCheck,
} from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { PRODUCT_TYPES, SUGGESTED_QUESTIONS, type DecisionKey } from "@/lib/copilot";
import { PageHeader } from "@/components/layout/PageHeader";
import { Alert } from "@/components/ui/Alert";
import { DecisionBadge } from "@/components/ui/DecisionBadge";
import { RiskBadge } from "@/components/ui/RiskBadge";
import { SourceCard, type SourceCardProps } from "@/components/ui/SourceCard";
import { Spinner } from "@/components/ui/Spinner";

const schema = z.object({
  question: z.string().min(5, "Descreva a operação em pelo menos 5 caracteres"),
  product_type: z.string().optional(),
  product_name_hint: z.string().optional(),
  amount: z.coerce.number().min(0).optional().or(z.literal("")),
  objective: z.string().optional(),
});
type Form = z.infer<typeof schema>;

export default function CopilotPage() {
  const router = useRouter();
  const { user } = useAuth();
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState("");
  const [showAdvanced, setShowAdvanced] = useState(false);
  const { register, handleSubmit, setValue, formState: { errors } } = useForm<Form>({ resolver: zodResolver(schema) });
  const mutation = useMutation({
    mutationFn: async (data: Form) => {
      const payload: Record<string, unknown> = { question: data.question };
      if (data.product_type) payload.product_type = data.product_type;
      if (data.product_name_hint) payload.product_name_hint = data.product_name_hint;
      if (data.amount) payload.amount = Number(data.amount);
      if (data.objective) payload.objective = data.objective;
      return api.post("/copilot/query", payload).then(response => response.data);
    },
    onSuccess: (data) => { setResult(data); setError(""); },
    onError: (requestError: any) => setError(requestError.response?.data?.detail ?? "Não foi possível analisar a operação. Tente novamente."),
  });
  const submit = (data: Form) => { setResult(null); setError(""); mutation.mutate(data); };
  const openPreApproval = () => router.push(result?.query_id ? `/pre-approvals/new?from_query=${result.query_id}` : "/pre-approvals/new");

  return (
    <div>
      <PageHeader title="Copilot de compliance" subtitle="Estruture a operação para aplicar regras e localizar evidências relevantes." action={<Link href="/history" className="btn-secondary"><History size={16} />Histórico</Link>} />
      {user?.role === "AUDITOR" ? (
        <Alert variant="info">Auditores possuem acesso somente leitura. Consulte as análises já registradas no histórico.</Alert>
      ) : (
        <div className="grid items-start gap-6 xl:grid-cols-[minmax(0,1fr)_340px]">
          <div className="space-y-6">
            <section className="card overflow-hidden">
              <div className="border-b border-slate-200 px-5 py-4"><h2 className="text-base font-semibold text-slate-950">Analisar uma operação</h2><p className="mt-1 text-sm text-slate-500">A decisão vem do motor de regras. Evidências e explicação aparecem separadamente.</p></div>
              <form onSubmit={handleSubmit(submit)} className="p-5 sm:p-6" noValidate>
                <div><label htmlFor="question" className="label">Pergunta sobre a operação <span className="text-red-700">*</span></label><textarea id="question" {...register("question")} rows={5} className="input resize-y text-[15px] leading-6" placeholder="Ex.: Posso comprar ações da XPTO3 no valor de R$ 20.000?" aria-invalid={Boolean(errors.question)} />{errors.question && <p className="field-error">{errors.question.message}</p>}</div>
                <button type="button" onClick={() => setShowAdvanced(value => !value)} className="mt-4 flex items-center gap-2 text-sm font-semibold text-brand-700 hover:text-brand-900" aria-expanded={showAdvanced}>{showAdvanced ? <ChevronUp size={16} /> : <ChevronDown size={16} />}{showAdvanced ? "Ocultar contexto estruturado" : "Adicionar contexto estruturado"}</button>
                {showAdvanced && <div className="mt-5 grid gap-4 border-t border-slate-200 pt-5 sm:grid-cols-2">
                  <div><label htmlFor="product_type" className="label">Tipo de produto</label><select id="product_type" {...register("product_type")} className="input"><option value="">Selecionar</option>{PRODUCT_TYPES.map(({ value, label }) => <option key={value} value={value}>{label}</option>)}</select></div>
                  <div><label htmlFor="product_name_hint" className="label">Produto ou ticker</label><input id="product_name_hint" {...register("product_name_hint")} className="input" placeholder="XPTO3 ou Fundo Alpha" /></div>
                  <div><label htmlFor="amount" className="label">Valor estimado</label><input id="amount" {...register("amount")} type="number" min={0} step={1000} className="input" placeholder="R$ 0,00" /></div>
                  <div><label htmlFor="objective" className="label">Objetivo</label><input id="objective" {...register("objective")} className="input" placeholder="Ex.: diversificação" /></div>
                </div>}
                {error && <Alert variant="error" className="mt-5">{error}</Alert>}
                {mutation.isPending && <div className="mt-5 rounded-lg border border-brand-200 bg-brand-50 p-4" role="status"><div className="flex items-center gap-3"><Spinner className="h-5 w-5" /><div><p className="text-sm font-semibold text-brand-950">Analisando a operação</p><p className="mt-0.5 text-xs text-brand-800">Aplicando regras estruturadas e procurando evidências documentais.</p></div></div></div>}
                <div className="mt-6 flex items-center justify-between gap-4 border-t border-slate-200 pt-5"><p className="hidden max-w-md text-xs leading-5 text-slate-500 sm:block">A IA redige a explicação, mas não altera a decisão, as regras aplicadas ou a próxima ação.</p><button type="submit" disabled={mutation.isPending} className="btn-primary ml-auto">{mutation.isPending ? "Analisando…" : <><Send size={16} />Analisar operação</>}</button></div>
              </form>
            </section>
            {result && <DecisionResult result={result} onOpenPreApproval={openPreApproval} />}
          </div>

          <aside className="space-y-5 xl:sticky xl:top-0">
            <section className="card p-5"><div className="flex items-center gap-2 text-brand-800"><ListChecks size={17} /><h2 className="text-sm font-semibold">Como a análise funciona</h2></div><ol className="mt-4 space-y-4">{[
              ["01", "Regras", "A decisão estruturada é calculada."], ["02", "Evidências", "O BM25 recupera trechos relevantes."], ["03", "Explicação", "O provider explica a decisão já tomada."],
            ].map(([number, title, text]) => <li key={number} className="grid grid-cols-[28px_1fr] gap-3"><span className="font-mono text-xs font-semibold text-brand-700">{number}</span><div><p className="text-sm font-semibold text-slate-800">{title}</p><p className="mt-0.5 text-xs leading-5 text-slate-500">{text}</p></div></li>)}</ol></section>
            {!result && <section><div className="mb-3 flex items-center gap-2"><MessageSquareText size={15} className="text-slate-500" /><h2 className="text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">Exemplos de consulta</h2></div><div className="space-y-2">{SUGGESTED_QUESTIONS.slice(0, 4).map(question => <button key={question} onClick={() => { setValue("question", question, { shouldValidate: true }); setShowAdvanced(false); }} className="group flex w-full items-start justify-between gap-3 rounded-lg border border-slate-200 bg-white p-3 text-left text-sm leading-5 text-slate-600 hover:border-brand-300 hover:bg-brand-50"><span>{question}</span><ArrowRight size={14} className="mt-0.5 shrink-0 text-slate-300 group-hover:text-brand-700" /></button>)}</div></section>}
          </aside>
        </div>
      )}
    </div>
  );
}

function DecisionResult({ result, onOpenPreApproval }: { result: any; onOpenPreApproval: () => void }) {
  const [showRules, setShowRules] = useState(true);
  const decision = result.decision as DecisionKey;
  const sources = (result.sources ?? []) as SourceCardProps[];
  return (
    <section className="card overflow-hidden" aria-label="Resultado da análise">
      <div className="border-b border-slate-200 bg-slate-50/70 p-5 sm:p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div><p className="meta-label mb-2">Decisão estruturada</p><div className="flex flex-wrap items-center gap-2"><DecisionBadge decision={decision} /><RiskBadge risk={result.risk_level} />{result.requires_human_review && <span className="inline-flex items-center gap-1.5 rounded-md bg-amber-50 px-2 py-1 text-xs font-semibold text-amber-900 ring-1 ring-inset ring-amber-700/20"><UserCheck size={13} />Aguarda decisão humana</span>}</div></div>
          <div className="text-right"><p className="meta-label">Confiança</p><p className="mt-1 text-xl font-semibold tabular-nums text-slate-950">{Math.round(result.confidence * 100)}%</p></div>
        </div>
        {result.next_action && <div className="mt-5 flex items-start gap-3 border-t border-slate-200 pt-4"><ArrowRight size={17} className="mt-0.5 shrink-0 text-brand-700" /><div><p className="text-xs font-semibold uppercase tracking-[0.08em] text-slate-500">Próxima ação</p><p className="mt-1 text-sm font-medium leading-6 text-slate-900">{result.next_action}</p></div></div>}
      </div>

      {result.out_of_scope ? <div className="p-5 sm:p-6"><Alert variant="warning">A pergunta está fora do escopo de compliance. Informe um produto ou uma operação financeira concreta.</Alert></div> : <div className="divide-y divide-slate-200">
        <section className="p-5 sm:p-6"><button onClick={() => setShowRules(value => !value)} className="flex w-full items-center justify-between text-left" aria-expanded={showRules}><span className="flex items-center gap-2"><ShieldCheck size={17} className="text-brand-700" /><span className="text-sm font-semibold text-slate-950">Fundamentação determinística</span></span>{showRules ? <ChevronUp size={16} /> : <ChevronDown size={16} />}</button>{showRules && <div className="mt-4">{result.matched_rules?.length ? <div className="flex flex-wrap gap-2">{result.matched_rules.map((rule: string) => <span key={rule} className="rounded-md bg-slate-100 px-2.5 py-1.5 font-mono text-xs font-semibold text-slate-700 ring-1 ring-inset ring-slate-300">{rule}</span>)}</div> : <p className="text-sm text-slate-500">Nenhuma regra configurada foi aplicável à operação.</p>}</div>}</section>
        <section className="p-5 sm:p-6"><div className="mb-3 flex items-center gap-2"><Info size={17} className="text-blue-700" /><h3 className="text-sm font-semibold text-slate-950">Explicação</h3><span className="ml-auto text-[10px] font-semibold uppercase tracking-[0.1em] text-slate-400">Camada explicativa</span></div><p className="max-w-3xl text-sm leading-7 text-slate-600">{result.justification}</p></section>
        <section className="p-5 sm:p-6"><div className="mb-4 flex items-center gap-2"><BookOpenText size={17} className="text-brand-700" /><h3 className="text-sm font-semibold text-slate-950">Evidências documentais</h3><span className="ml-auto text-xs tabular-nums text-slate-500">{sources.length} {sources.length === 1 ? "fonte" : "fontes"}</span></div>{sources.length ? <div className="space-y-3">{sources.map((source, index) => <SourceCard key={`${source.document_name}-${index}`} source={source} />)}</div> : <div className="rounded-lg border border-dashed border-slate-300 px-4 py-7 text-center"><Search className="mx-auto text-slate-300" size={21} /><p className="mt-2 text-sm font-medium text-slate-700">Nenhuma evidência relevante recuperada</p><p className="mt-1 text-xs text-slate-500">O relevance gate omitiu trechos sem relação suficiente.</p></div>}</section>
      </div>}

      <div className="flex flex-wrap gap-3 border-t border-slate-200 bg-white p-5 sm:px-6">
        {decision === "PRE_APPROVAL_REQUIRED" && <button onClick={onOpenPreApproval} className="btn-primary"><ClipboardCheck size={16} />Solicitar pré-aprovação</button>}
        {decision === "INCONCLUSIVE" && <button onClick={onOpenPreApproval} className="btn-secondary"><UserCheck size={16} />Solicitar revisão humana</button>}
        {result.query_id && <Link href={`/history/${result.query_id}`} className="btn-ghost"><History size={16} />Abrir registro histórico</Link>}
        {decision === "RESTRICTED" && <p className="flex items-center gap-2 text-sm font-semibold text-red-800"><FileCheck2 size={16} />A operação não deve ser executada.</p>}
      </div>
    </section>
  );
}
