"use client";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { PageHeader } from "@/components/layout/PageHeader";
import { Spinner } from "@/components/ui/Spinner";
import { EmptyState } from "@/components/ui/EmptyState";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { RiskBadge } from "@/components/ui/RiskBadge";
import { SkeletonRows } from "@/components/ui/Skeleton";
import {
  PRODUCT_TYPES, PRODUCT_TYPE_MAP,
  STATUS_OPTIONS, STATUS_MAP,
  RISK_OPTIONS,
} from "@/lib/products";
import { Package, Search, X } from "lucide-react";

export default function ProductsPage() {
  const { user } = useAuth();
  const canEdit = user && ["ADMIN", "COMPLIANCE"].includes(user.role);

  const [search, setSearch]   = useState("");
  const [typeF, setTypeF]     = useState("");
  const [statusF, setStatusF] = useState("");
  const [riskF, setRiskF]     = useState("");

  const params = new URLSearchParams();
  if (search)  params.set("q", search);
  if (typeF)   params.set("product_type", typeF);
  if (statusF) params.set("status", statusF);
  if (riskF)   params.set("risk", riskF);

  const { data: products = [], isLoading } = useQuery({
    queryKey: ["products", search, typeF, statusF, riskF],
    queryFn: () => api.get(`/products?${params}`).then((r) => r.data),
  });

  const hasFilters = search || typeF || statusF || riskF;

  const clearFilters = () => {
    setSearch(""); setTypeF(""); setStatusF(""); setRiskF("");
  };

  return (
    <div>
      <PageHeader
        title="Produtos Financeiros"
        subtitle={`${products.length} resultado${products.length !== 1 ? "s" : ""}`}
        action={
          canEdit && (
            <Link href="/products/new" className="btn-primary text-sm">
              + Novo produto
            </Link>
          )
        }
      />

      {/* barra de filtros */}
      <div className="mb-5 flex flex-wrap gap-3 rounded-lg border border-slate-200 bg-white p-3">
        <div className="relative flex-1 min-w-48">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="input pl-8"
            placeholder="Buscar por nome ou identificador…"
          />
        </div>

        <select value={typeF} onChange={(e) => setTypeF(e.target.value)} className="input w-44">
          <option value="">Tipo</option>
          {PRODUCT_TYPES.map(({ value, label }) => (
            <option key={value} value={value}>{label}</option>
          ))}
        </select>

        <select value={statusF} onChange={(e) => setStatusF(e.target.value)} className="input w-40">
          <option value="">Status</option>
          {STATUS_OPTIONS.map(({ value, label }) => (
            <option key={value} value={value}>{label}</option>
          ))}
        </select>

        <select value={riskF} onChange={(e) => setRiskF(e.target.value)} className="input w-36">
          <option value="">Risco</option>
          {RISK_OPTIONS.map(({ value, label }) => (
            <option key={value} value={value}>{label}</option>
          ))}
        </select>

        {hasFilters && (
          <button onClick={clearFilters}
            className="flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-700 px-3 py-2 rounded-lg hover:bg-slate-100 transition-colors">
            <X size={14} /> Limpar
          </button>
        )}
      </div>

      {isLoading ? (
        <div className="card p-4"><SkeletonRows rows={7} /></div>
      ) : products.length === 0 ? (
        <EmptyState
          message={hasFilters ? "Nenhum produto corresponde aos filtros." : "Nenhum produto cadastrado."}
          icon={<Package />}
        />
      ) : (
        <div className="card overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-xs text-slate-500 uppercase tracking-wide">
              <tr>
                <th className="px-4 py-3 text-left">Nome</th>
                <th className="px-4 py-3 text-left">Tipo</th>
                <th className="px-4 py-3 text-left">Identificador</th>
                <th className="px-4 py-3 text-left">Emissor</th>
                <th className="px-4 py-3 text-left">Status</th>
                <th className="px-4 py-3 text-left">Risco</th>
                <th className="px-4 py-3 text-left">Liquidez</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {products.map((p: any) => (
                <tr key={p.id} className="hover:bg-slate-50 transition-colors">
                  <td className="px-4 py-3">
                    <Link href={`/products/${p.id}`}
                      className="font-medium text-brand-600 hover:underline">
                      {p.name}
                    </Link>
                    {p.tags?.length > 0 && (
                      <div className="flex gap-1 mt-1 flex-wrap">
                        {p.tags.map((t: string) => (
                          <span key={t} className="text-xs bg-slate-100 text-slate-500 px-1.5 py-0.5 rounded">
                            {t}
                          </span>
                        ))}
                      </div>
                    )}
                  </td>
                  <td className="px-4 py-3 text-slate-500">
                    {PRODUCT_TYPE_MAP[p.product_type] ?? p.product_type}
                  </td>
                  <td className="px-4 py-3 font-mono text-xs text-slate-600">
                    {p.identifier ?? "—"}
                  </td>
                  <td className="px-4 py-3 text-slate-500">{p.issuer ?? "—"}</td>
                  <td className="px-4 py-3">
                    <StatusBadge status={p.status} label={STATUS_MAP[p.status] ?? p.status} />
                  </td>
                  <td className="px-4 py-3">
                    {p.risk ? (
                      <RiskBadge risk={p.risk} />
                    ) : "—"}
                  </td>
                  <td className="px-4 py-3 text-slate-500 text-xs">{p.liquidity ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
