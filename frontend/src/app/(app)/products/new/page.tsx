"use client";
import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { PageHeader } from "@/components/layout/PageHeader";
import { ProductForm } from "@/components/ProductForm";
import type { ProductFormData } from "@/components/ProductForm";

export default function NewProductPage() {
  const router = useRouter();
  const qc = useQueryClient();
  const [error, setError] = useState("");

  const mutation = useMutation({
    mutationFn: (d: ProductFormData & { tags: string[] }) => {
      const { tags_raw, ...rest } = d;
      return api.post("/products", rest);
    },
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: ["products"] });
      router.push(`/products/${res.data.id}`);
    },
    onError: (e: any) => setError(e.response?.data?.detail ?? "Erro ao criar produto"),
  });

  return (
    <div className="max-w-5xl">
      <PageHeader eyebrow="Cadastro de produtos" title="Novo produto" subtitle="Registre a identidade, classificação e controles aplicáveis ao produto." />
      <div className="card p-6">
        <ProductForm
          submitLabel="Criar produto"
          isPending={mutation.isPending}
          error={error}
          onCancel={() => router.push("/products")}
          onSubmit={(d) => { setError(""); mutation.mutate(d); }}
        />
      </div>
    </div>
  );
}
