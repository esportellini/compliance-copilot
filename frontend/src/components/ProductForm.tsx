"use client";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Alert } from "@/components/ui/Alert";
import { Spinner } from "@/components/ui/Spinner";
import {
  PRODUCT_TYPES, STATUS_OPTIONS, RISK_OPTIONS, LIQUIDITY_OPTIONS,
} from "@/lib/products";

const schema = z.object({
  name:            z.string().min(2, "Nome obrigatório"),
  product_type:    z.string().min(1, "Tipo obrigatório"),
  identifier:      z.string().optional(),
  issuer:          z.string().optional(),
  manager:         z.string().optional(),
  administrator:   z.string().optional(),
  risk:            z.string().optional(),
  liquidity:       z.string().optional(),
  target_audience: z.string().optional(),
  status:          z.string(),
  notes:           z.string().optional(),
  tags_raw:        z.string().optional(),   // "tag1, tag2" — convertido antes do submit
});

export type ProductFormData = z.infer<typeof schema>;

interface Props {
  defaultValues?: Partial<ProductFormData>;
  onSubmit: (data: ProductFormData & { tags: string[] }) => void;
  onCancel: () => void;
  isPending: boolean;
  error: string;
  submitLabel: string;
}

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

export function ProductForm({ defaultValues, onSubmit, onCancel, isPending, error, submitLabel }: Props) {
  const { register, handleSubmit, formState: { errors } } = useForm<ProductFormData>({
    resolver: zodResolver(schema),
    defaultValues: { status: "ALLOWED", ...defaultValues },
  });

  const handleFormSubmit = (data: ProductFormData) => {
    const tags = data.tags_raw
      ? data.tags_raw.split(",").map((t) => t.trim()).filter(Boolean)
      : [];
    onSubmit({ ...data, tags });
  };

  return (
    <form onSubmit={handleSubmit(handleFormSubmit)} className="space-y-5">
      {error && <Alert variant="error">{error}</Alert>}

      {/* linha 1 */}
      <div className="grid grid-cols-2 gap-4">
        <Field label="Nome *" error={errors.name?.message}>
          <input {...register("name")} className="input" placeholder="Ex: Fundo Multimercado Alfa" />
        </Field>
        <Field label="Tipo *" error={errors.product_type?.message}>
          <select {...register("product_type")} className="input">
            <option value="">Selecionar…</option>
            {PRODUCT_TYPES.map(({ value, label }) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </select>
        </Field>
      </div>

      {/* linha 2 */}
      <div className="grid grid-cols-3 gap-4">
        <Field label="Ticker / CNPJ" error={errors.identifier?.message}>
          <input {...register("identifier")} className="input" placeholder="Ex: ALFA11 ou 00.000.000/0001-00" />
        </Field>
        <Field label="Status">
          <select {...register("status")} className="input">
            {STATUS_OPTIONS.map(({ value, label }) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </select>
        </Field>
        <Field label="Risco">
          <select {...register("risk")} className="input">
            <option value="">Selecionar…</option>
            {RISK_OPTIONS.map(({ value, label }) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </select>
        </Field>
      </div>

      {/* linha 3 */}
      <div className="grid grid-cols-3 gap-4">
        <Field label="Emissor">
          <input {...register("issuer")} className="input" placeholder="Ex: Banco Exemplo S.A." />
        </Field>
        <Field label="Gestor">
          <input {...register("manager")} className="input" placeholder="Ex: Gestora Exemplo" />
        </Field>
        <Field label="Administrador">
          <input {...register("administrator")} className="input" placeholder="Ex: Admin Exemplo" />
        </Field>
      </div>

      {/* linha 4 */}
      <div className="grid grid-cols-2 gap-4">
        <Field label="Liquidez">
          <select {...register("liquidity")} className="input">
            <option value="">Selecionar…</option>
            {LIQUIDITY_OPTIONS.map((l) => (
              <option key={l} value={l}>{l}</option>
            ))}
          </select>
        </Field>
        <Field label="Público-alvo">
          <input {...register("target_audience")} className="input"
            placeholder="Ex: Investidor qualificado" />
        </Field>
      </div>

      {/* notas */}
      <Field label="Observações">
        <textarea {...register("notes")} rows={3} className="input resize-none"
          placeholder="Informações adicionais sobre o produto…" />
      </Field>

      {/* tags */}
      <Field label="Tags" hint="Separe por vírgula: ex: câmbio, high-yield, offshore">
        <input {...register("tags_raw")} className="input" placeholder="tag1, tag2, tag3" />
      </Field>

      <div className="flex justify-end gap-3 pt-2 border-t border-slate-100">
        <button type="button" onClick={onCancel} className="btn-ghost text-sm">Cancelar</button>
        <button type="submit" disabled={isPending}
          className="btn-primary text-sm flex items-center gap-2">
          {isPending && <Spinner className="h-4 w-4 border-white border-t-transparent" />}
          {submitLabel}
        </button>
      </div>
    </form>
  );
}