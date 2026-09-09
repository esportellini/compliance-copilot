"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { ArrowRight, CheckCircle2, LockKeyhole, ShieldCheck } from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { Alert } from "@/components/ui/Alert";
import { Spinner } from "@/components/ui/Spinner";

const schema = z.object({ email: z.string().email("Informe um e-mail válido"), password: z.string().min(1, "Informe a senha") });
type Form = z.infer<typeof schema>;

const DEMO_ACCOUNTS = [
  { label: "Colaborador", email: "colaborador@demo.local" },
  { label: "Compliance", email: "compliance@demo.local" },
  { label: "Auditor", email: "auditor@demo.local" },
  { label: "Admin", email: "admin@demo.local" },
];

export default function LoginPage() {
  const { login } = useAuth();
  const router = useRouter();
  const [error, setError] = useState("");
  const { register, handleSubmit, setValue, formState: { errors, isSubmitting } } = useForm<Form>({ resolver: zodResolver(schema) });

  const onSubmit = async (data: Form) => {
    setError("");
    try { await login(data.email, data.password); router.push("/dashboard"); }
    catch { setError("Não foi possível entrar. Confira o e-mail e a senha de demonstração."); }
  };

  const fillDemoAccount = (email: string) => {
    setValue("email", email, { shouldValidate: true });
    setValue("password", "Compliance123!", { shouldValidate: true });
    setError("");
  };

  return (
    <main className="min-h-screen bg-[#eef0eb] p-3 sm:p-6">
      <div className="mx-auto grid min-h-[calc(100vh-24px)] max-w-[1180px] overflow-hidden rounded-xl border border-slate-200 bg-white shadow-[0_24px_70px_rgba(24,34,29,0.14)] sm:min-h-[calc(100vh-48px)] lg:grid-cols-[1.08fr_0.92fr]">
        <section className="relative flex flex-col justify-between overflow-hidden bg-brand-950 p-6 text-white sm:p-10 lg:p-14">
          <div className="absolute inset-x-0 top-[38%] border-t border-white/10" aria-hidden="true" />
          <div className="absolute inset-x-0 top-[62%] border-t border-white/10" aria-hidden="true" />
          <div className="relative flex items-center gap-3">
            <span className="flex h-10 w-10 items-center justify-center rounded-lg border border-white/15 bg-white/10"><ShieldCheck size={22} strokeWidth={1.8} aria-hidden="true" /></span>
            <div><p className="text-base font-semibold">Compliance Copilot</p><p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-brand-200">Control workspace</p></div>
          </div>
          <div className="relative my-8 max-w-lg sm:my-12 lg:my-0">
            <p className="text-2xl font-semibold leading-tight tracking-[-0.035em] sm:text-4xl">Decisões de compliance com estrutura, evidência e rastreabilidade.</p>
            <p className="mt-4 max-w-md text-sm leading-7 text-brand-100">Rules decide. Evidence supports. AI explains.</p>
          </div>
          <div className="relative hidden gap-3 text-sm text-brand-100 sm:grid sm:grid-cols-3 lg:grid-cols-1">
            {["Regras determinísticas", "Evidência documental", "Aprovação humana quando exigida"].map((item) => <div key={item} className="flex items-center gap-2"><CheckCircle2 size={15} className="text-brand-300" aria-hidden="true" />{item}</div>)}
          </div>
        </section>

        <section className="flex items-center justify-center p-6 sm:p-10 lg:p-14">
          <div className="w-full max-w-md">
            <div className="mb-8">
              <div className="mb-5 flex h-10 w-10 items-center justify-center rounded-lg bg-brand-50 text-brand-800"><LockKeyhole size={20} aria-hidden="true" /></div>
              <h1 className="text-2xl font-semibold tracking-[-0.025em] text-slate-950">Acesse seu workspace</h1>
              <p className="mt-2 text-sm leading-6 text-slate-500">Ambiente fictício para demonstração dos fluxos do produto.</p>
            </div>
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-5" noValidate>
              {error && <Alert variant="error">{error}</Alert>}
              <div><label htmlFor="email" className="label">E-mail</label><input id="email" {...register("email")} type="email" autoComplete="username" className="input" placeholder="nome@demo.local" aria-invalid={Boolean(errors.email)} />{errors.email && <p className="field-error">{errors.email.message}</p>}</div>
              <div><div className="flex items-center justify-between"><label htmlFor="password" className="label">Senha</label><span className="mb-1.5 text-xs text-slate-400">Exclusiva para demo</span></div><input id="password" {...register("password")} type="password" autoComplete="current-password" className="input" placeholder="Digite a senha" aria-invalid={Boolean(errors.password)} />{errors.password && <p className="field-error">{errors.password.message}</p>}</div>
              <button type="submit" disabled={isSubmitting} className="btn-primary w-full">
                {isSubmitting ? <><Spinner className="h-4 w-4 border-white/40 border-t-white" />Autenticando…</> : <>Entrar<ArrowRight size={16} aria-hidden="true" /></>}
              </button>
            </form>
            <div className="mt-8 border-t border-slate-200 pt-6">
              <div className="mb-3 flex items-center justify-between"><p className="text-xs font-semibold uppercase tracking-[0.1em] text-slate-500">Acessos de demonstração</p><p className="font-mono text-[11px] text-slate-400">Compliance123!</p></div>
              <div className="grid grid-cols-2 gap-2">
                {DEMO_ACCOUNTS.map((account) => <button key={account.email} type="button" onClick={() => fillDemoAccount(account.email)} className="rounded-md border border-slate-200 px-3 py-2 text-left hover:border-brand-300 hover:bg-brand-50"><span className="block text-xs font-semibold text-slate-800">{account.label}</span><span className="mt-0.5 block truncate text-[10px] text-slate-500">{account.email}</span></button>)}
              </div>
              <p className="mt-4 text-xs leading-5 text-slate-500">Credenciais públicas, fictícias e inseguras. Não reutilize em ambientes reais.</p>
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
