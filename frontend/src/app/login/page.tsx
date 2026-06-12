"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useAuth } from "@/lib/auth-context";
import { Alert } from "@/components/ui/Alert";
import { Spinner } from "@/components/ui/Spinner";

const schema = z.object({
  email: z.string().email("E-mail inválido"),
  password: z.string().min(1, "Obrigatório"),
});
type Form = z.infer<typeof schema>;

export default function LoginPage() {
  const { login } = useAuth();
  const router = useRouter();
  const [error, setError] = useState("");
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<Form>({ resolver: zodResolver(schema) });

  const onSubmit = async (data: Form) => {
    setError("");
    try {
      await login(data.email, data.password);
      router.push("/dashboard");
    } catch {
      setError("Credenciais inválidas. Verifique e-mail e senha.");
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-brand-900 to-brand-600 flex items-center justify-center p-4">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold text-white">Compliance Copilot</h1>
          <p className="text-brand-100 text-sm mt-1 opacity-80">Acesso restrito a colaboradores autorizados</p>
        </div>
        <div className="card p-8">
          <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4">
            {error && <Alert variant="error">{error}</Alert>}
            <div>
              <label className="label">E-mail</label>
              <input {...register("email")} type="email" className="input" placeholder="seu@empresa.com" />
              {errors.email && <p className="text-xs text-red-600 mt-1">{errors.email.message}</p>}
            </div>
            <div>
              <label className="label">Senha</label>
              <input {...register("password")} type="password" className="input" placeholder="••••••••" />
              {errors.password && <p className="text-xs text-red-600 mt-1">{errors.password.message}</p>}
            </div>
            <button type="submit" disabled={isSubmitting} className="btn-primary w-full flex items-center justify-center gap-2 mt-2">
              {isSubmitting && <Spinner className="h-4 w-4 border-white border-t-transparent" />}
              Entrar
            </button>
          </form>
        </div>
        <p className="text-center text-xs text-brand-200 mt-6 opacity-60">
          ⚠️ Ambiente de demonstração. Não use credenciais reais.
        </p>
      </div>
    </div>
  );
}