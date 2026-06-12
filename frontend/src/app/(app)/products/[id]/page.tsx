"use client";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { PageHeader } from "@/components/layout/PageHeader";
import { Alert } from "@/components/ui/Alert";
import { Spinner } from "@/components/ui/Spinner";
import { DecisionBadge } from "@/components/ui/DecisionBadge";
import { ProductForm } from "@/components/ProductForm";
import type { ProductFormData } from "@/components/ProductForm";
import {
  PRODUCT_TYPE_MAP, STATUS_BADGE, STATUS_MAP, RISK_BADGE, RISK_MAP,
} from "@/lib/products";
import { fmtDateTime } from "@/lib/utils";
import { Pencil, ShieldAlert, ShieldBan, ChevronLeft, X } from "lucide-react";

// ─── modal de confirmação ──────────────────────────────────────────────────────
function ConfirmModal({
  title, body, confirmLabel, confirmClass, onConfirm, onClose, isPending,
}: {
  title: string; body: string; confirmLabel: string; confirmClass: string;
  onConfirm: () => void; onClose: () => void; isPending: boolean;
}) {
  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-sm">
        <div className="flex items-start justify-between px-6 py-4 border-b border-slate-100">
          <h2 className="font-semibold text-slate-800">{title}</h2>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600 ml-4">
            <X size={18} />
          </button>
        </div>
        <div className="px-6 py-5">
          <p className="text-sm text-slate-600">{body}</p>
          <div className="flex justify-end gap-3 mt-6">
            <button onClick={onClose} className="btn-ghost text-sm">Cancelar</button>
            <button onClick={onConfirm} disabled={isPending}
              className={`text-sm font-medium px-4 py-2 rounded-lg text-white transition-colors flex items-center gap-2 ${confirmClass}`}>
              {isPending && <Spinner className="h-4 w-4 border-white border-t-transparent" />}
              {confirmLabel}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── linha de detalhe ──────────────────────────────────────────────────────────
function DetailRow({ label, value }: { label: string; value?: string | null }) {
  if (!value) return null;
  return (
    <div className="flex gap-2">
      <span className="w-36 shrink-0 text-xs text-slate-500 pt-0.5">{label}</span>
      <span className="text-sm text-slate-800">{value}</span>
    </div>
  );
}

// ─── página principal ──────────────────────────────────────────────────────────
export default function ProductDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();
  const router = useRouter();
  const qc = useQueryClient();
  const canEdit = user && ["ADMIN", "COMPLIANCE"].includes(user.role);

  const [editing, setEditing]         = useState(false);
  const [confirm, setConfirm]         = useState<"restrict" | "block" | null>(null);
  const [editError, setEditError]     = useState("");

  const { data: product, isLoading } = useQuery({
    queryKey: ["product", id],
    queryFn: () => api.get(`/products/${id}`).then((r) => r.data),
  });

  const { data: queries = [] } = useQuery({
    queryKey: ["product-queries", id],
    queryFn: () => api.get(`/products/${id}/queries`).then((r) => r.data),
    enabled: !!id,
  });

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["product", id] });
    qc.invalidateQueries({ queryKey: ["products"] });
  };

  const editMutation = useMutation({
    mutationFn: (d: ProductFormData & { tags: string[] }) => {
      const { tags_raw, ...rest } = d;
      return api.patch(`/products/${id}`, rest);
    },
    onSuccess: () => { invalidate(); setEditing(false); },
    onError: (e: any) => setEditError(e.response?.data?.detail ?? "Erro ao salvar"),
  });

  const restrictMutation = useMutation({
    mutationFn: () => api.patch(`/products/${id}/restrict`),
    onSuccess: () => { invalidate(); setConfirm(null); },
  });

  const blockMutation = useMutation({
    mutationFn: () => api.patch(`/products/${id}/block`),
    onSuccess: () => { invalidate(); setConfirm(null); },
  });

  if (isLoading) return (
    <div className="flex justify-center py-20"><Spinner className="h-8 w-8" /></div>
  );
  if (!product) return <Alert variant="error">Produto não encontrado.</Alert>;

  const statusBadge = STATUS_BADGE[product.status] ?? "bg-slate-100 text-slate-600";
  const riskBadge   = product.risk ? (RISK_BADGE[product.risk] ?? "bg-slate-100 text-slate-500") : null;

  return (
    <div className="max-w-3xl">
      {/* cabeçalho */}
      <div className="flex items-center gap-2 text-sm text-slate-500 mb-4">
        <Link href="/products" className="hover:text-brand-600 flex items-center gap-1">
          <ChevronLeft size={14} /> Produtos
        </Link>
        <span>/</span>
        <span className="text-slate-700">{product.name}</span>
      </div>

      <PageHeader
        title={product.name}
        subtitle={PRODUCT_TYPE_MAP[product.product_type] ?? product.product_type}
        action={
          canEdit && !editing && (
            <div className="flex gap-2">
              {product.status !== "BLOCKED" && (
                <button onClick={() => setConfirm("block")}
                  className="flex items-center gap-1.5 text-sm text-red-600 border border-red-200 hover:bg-red-50 px-3 py-2 rounded-lg transition-colors">
                  <ShieldBan size={14} /> Bloquear
                </button>
              )}
              {!["RESTRICTED", "BLOCKED"].includes(product.status) && (
                <button onClick={() => setConfirm("restrict")}
                  className="flex items-center gap-1.5 text-sm text-amber-600 border border-amber-200 hover:bg-amber-50 px-3 py-2 rounded-lg transition-colors">
                  <ShieldAlert size={14} /> Restringir
                </button>
              )}
              <button onClick={() => { setEditing(true); setEditError(""); }}
                className="flex items-center gap-1.5 btn-primary text-sm">
                <Pencil size={14} /> Editar
              </button>
            </div>
          )
        }
      />

      {/* badges de status */}
      <div className="flex items-center gap-2 mb-6">
        <span className={`text-xs font-medium px-2.5 py-1 rounded-full ${statusBadge}`}>
          {STATUS_MAP[product.status] ?? product.status}
        </span>
        {riskBadge && (
          <span className={`text-xs font-medium px-2.5 py-1 rounded-full ${riskBadge}`}>
            Risco {RISK_MAP[product.risk]}
          </span>
        )}
        {product.tags?.map((t: string) => (
          <span key={t} className="text-xs bg-slate-100 text-slate-500 px-2 py-0.5 rounded">
            {t}
          </span>
        ))}
      </div>

      {/* formulário de edição */}
      {editing && (
        <div className="card p-6 mb-6">
          <h2 className="text-sm font-semibold text-slate-700 mb-4">Editar produto</h2>
          <ProductForm
            defaultValues={{
              name:            product.name,
              product_type:    product.product_type,
              identifier:      product.identifier ?? "",
              issuer:          product.issuer ?? "",
              manager:         product.manager ?? "",
              administrator:   product.administrator ?? "",
              risk:            product.risk ?? "",
              liquidity:       product.liquidity ?? "",
              target_audience: product.target_audience ?? "",
              status:          product.status,
              notes:           product.notes ?? "",
              tags_raw:        (product.tags ?? []).join(", "),
            }}
            onSubmit={(d) => { setEditError(""); editMutation.mutate(d); }}
            onCancel={() => setEditing(false)}
            isPending={editMutation.isPending}
            error={editError}
            submitLabel="Salvar alterações"
          />
        </div>
      )}

      {/* dados completos */}
      {!editing && (
        <div className="card p-6 mb-6">
          <h2 className="text-sm font-semibold text-slate-700 mb-4">Dados do produto</h2>
          <div className="space-y-2.5">
            <DetailRow label="Identificador"   value={product.identifier} />
            <DetailRow label="Emissor"         value={product.issuer} />
            <DetailRow label="Gestor"          value={product.manager} />
            <DetailRow label="Administrador"   value={product.administrator} />
            <DetailRow label="Liquidez"        value={product.liquidity} />
            <DetailRow label="Público-alvo"    value={product.target_audience} />
            <DetailRow label="Cadastrado em"   value={fmtDateTime(product.created_at)} />
            <DetailRow label="Atualizado em"   value={fmtDateTime(product.updated_at)} />
          </div>
          {product.notes && (
            <div className="mt-4 pt-4 border-t border-slate-100">
              <p className="text-xs text-slate-500 mb-1">Observações</p>
              <p className="text-sm text-slate-700 whitespace-pre-wrap">{product.notes}</p>
            </div>
          )}
        </div>
      )}

      {/* histórico de consultas */}
      <div className="card">
        <div className="px-5 py-4 border-b border-slate-100">
          <h2 className="text-sm font-semibold text-slate-700">
            Consultas relacionadas
            {queries.length > 0 && (
              <span className="ml-2 text-xs font-normal text-slate-400">{queries.length}</span>
            )}
          </h2>
        </div>
        {queries.length === 0 ? (
          <p className="px-5 py-8 text-sm text-slate-400 text-center">
            Nenhuma consulta do Copilot referencia este produto ainda.
          </p>
        ) : (
          <div className="divide-y divide-slate-50">
            {queries.map((q: any) => (
              <div key={q.id} className="px-5 py-3 flex items-center gap-4">
                <Link href={`/history/${q.id}`}
                  className="flex-1 text-sm text-slate-700 hover:text-brand-600 line-clamp-1">
                  {q.question}
                </Link>
                {q.decision && <DecisionBadge decision={q.decision} />}
                <span className="text-xs text-slate-400 shrink-0">{fmtDateTime(q.created_at)}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* modal: restringir */}
      {confirm === "restrict" && (
        <ConfirmModal
          title="Marcar como restrito"
          body={`Tem certeza que deseja marcar "${product.name}" como RESTRITO? Colaboradores não poderão operar este produto sem pré-aprovação. Esta ação gera registro de auditoria.`}
          confirmLabel="Restringir"
          confirmClass="bg-amber-500 hover:bg-amber-600"
          onConfirm={() => restrictMutation.mutate()}
          onClose={() => setConfirm(null)}
          isPending={restrictMutation.isPending}
        />
      )}

      {/* modal: bloquear */}
      {confirm === "block" && (
        <ConfirmModal
          title="Bloquear produto"
          body={`Tem certeza que deseja BLOQUEAR "${product.name}"? Nenhuma operação será permitida. Esta ação gera registro de auditoria e não pode ser revertida sem revisão manual.`}
          confirmLabel="Bloquear"
          confirmClass="bg-red-600 hover:bg-red-700"
          onConfirm={() => blockMutation.mutate()}
          onClose={() => setConfirm(null)}
          isPending={blockMutation.isPending}
        />
      )}
    </div>
  );
}