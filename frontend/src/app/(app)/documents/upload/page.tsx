"use client";
import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { api } from "@/lib/api";
import { PageHeader } from "@/components/layout/PageHeader";
import { Alert } from "@/components/ui/Alert";
import { Spinner } from "@/components/ui/Spinner";
import { DOCUMENT_TYPES } from "@/lib/documents";
import { UploadCloud, FileText, X } from "lucide-react";
import Link from "next/link";

const schema = z.object({
  name:           z.string().min(3, "Mínimo 3 caracteres"),
  doc_type:       z.string().min(1, "Selecione um tipo"),
  version:        z.string().optional(),
  owner:          z.string().optional(),
  effective_date: z.string().optional(),
});
type Form = z.infer<typeof schema>;

function Field({ label, hint, error, children }: {
  label: string; hint?: string; error?: string; children: React.ReactNode;
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

export default function UploadPage() {
  const router = useRouter();
  const qc = useQueryClient();
  const [file, setFile]     = useState<File | null>(null);
  const [error, setError]   = useState("");
  const [dragOver, setDrag] = useState(false);

  const { register, handleSubmit, formState: { errors } } = useForm<Form>({
    resolver: zodResolver(schema),
    defaultValues: { doc_type: "" },
  });

  const mutation = useMutation({
    mutationFn: async (data: Form) => {
      if (!file) throw new Error("Selecione um arquivo.");
      const form = new FormData();
      form.append("file", file);
      form.append("name", data.name);
      form.append("doc_type", data.doc_type);
      if (data.version)        form.append("version", data.version);
      if (data.owner)          form.append("owner", data.owner);
      if (data.effective_date) form.append("effective_date", data.effective_date);
      return api.post("/documents/upload", form, { headers: { "Content-Type": "multipart/form-data" } });
    },
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: ["documents"] });
      router.push(`/documents/${res.data.id}`);
    },
    onError: (e: any) => setError(e.response?.data?.detail ?? e.message ?? "Erro ao enviar"),
  });

  const handleFile = (f: File) => {
    const ext = f.name.split(".").pop()?.toLowerCase();
    if (!["pdf", "docx", "txt"].includes(ext ?? "")) {
      setError("Formato não suportado. Use PDF, DOCX ou TXT.");
      return;
    }
    setError("");
    setFile(f);
  };

  return (
    <div className="max-w-4xl">
      <div className="flex items-center gap-2 text-sm text-slate-500 mb-4">
        <Link href="/documents" className="hover:text-brand-600">Documentos</Link>
        <span>/</span>
        <span className="text-slate-700">Enviar documento</span>
      </div>

      <PageHeader title="Enviar documento" subtitle="PDF, DOCX ou TXT · máx 20 MB" />

      <form onSubmit={handleSubmit((d) => { setError(""); mutation.mutate(d); })} className="space-y-5">
        {error && <Alert variant="error">{error}</Alert>}

        {/* dropzone */}
        <div
          className={`border border-dashed rounded-lg p-8 text-center transition-colors
            ${dragOver ? "border-brand-400 bg-brand-50" : "border-slate-300 hover:border-brand-300 hover:bg-slate-50"}`}
          onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
          onDragLeave={() => setDrag(false)}
          onDrop={(e) => {
            e.preventDefault(); setDrag(false);
            const f = e.dataTransfer.files[0];
            if (f) handleFile(f);
          }}
        >
          <input id="document-file" type="file" accept=".pdf,.docx,.txt" className="sr-only"
            onChange={(e) => { const f = e.target.files?.[0]; if (f) handleFile(f); }} />
          {file ? (
            <div className="flex items-center justify-center gap-3">
              <FileText size={24} className="text-brand-500 shrink-0" />
              <div className="text-left">
                <p className="text-sm font-medium text-slate-800">{file.name}</p>
                <p className="text-xs text-slate-400">
                  {(file.size / 1024).toFixed(1)} KB · {file.type || "desconhecido"}
                </p>
              </div>
              <button type="button" onClick={() => setFile(null)}
                className="ml-2 rounded-md p-1 text-slate-500 hover:bg-red-50 hover:text-red-700" aria-label="Remover arquivo selecionado">
                <X size={16} />
              </button>
            </div>
          ) : (
            <label htmlFor="document-file" className="block cursor-pointer">
              <UploadCloud size={32} className="mx-auto text-slate-300 mb-2" />
              <p className="text-sm text-slate-500">Arraste o arquivo ou clique para selecionar</p>
              <p className="text-xs text-slate-400 mt-1">PDF, DOCX ou TXT · máx 20 MB</p>
            </label>
          )}
        </div>

        <div className="card p-5 space-y-4">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <Field label="Nome do documento *" error={errors.name?.message}>
              <input {...register("name")} className="input" placeholder="Ex: Código de Ética 2024" />
            </Field>
            <Field label="Tipo *" error={errors.doc_type?.message}>
              <select {...register("doc_type")} className="input">
                <option value="">Selecionar…</option>
                {DOCUMENT_TYPES.map(({ value, label }) => (
                  <option key={value} value={value}>{label}</option>
                ))}
              </select>
            </Field>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <Field label="Versão" hint="Obrigatório para ativar">
              <input {...register("version")} className="input" placeholder="Ex: 2.1" />
            </Field>
            <Field label="Responsável" hint="Obrigatório para ativar">
              <input {...register("owner")} className="input" placeholder="Ex: compliance@firma.com" />
            </Field>
            <Field label="Data de vigência">
              <input {...register("effective_date")} type="date" className="input" />
            </Field>
          </div>
        </div>

        <div className="flex justify-end gap-3">
          <Link href="/documents" className="btn-ghost text-sm">Cancelar</Link>
          <button type="submit" disabled={mutation.isPending || !file}
            className="btn-primary text-sm flex items-center gap-2">
            {mutation.isPending && <Spinner className="h-4 w-4 border-white border-t-transparent" />}
            Enviar documento
          </button>
        </div>
      </form>
    </div>
  );
}
