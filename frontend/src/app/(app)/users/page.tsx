"use client";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { PageHeader } from "@/components/layout/PageHeader";
import { Spinner } from "@/components/ui/Spinner";
import { EmptyState } from "@/components/ui/EmptyState";
import { Alert } from "@/components/ui/Alert";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { SkeletonRows } from "@/components/ui/Skeleton";
import { ROLE_LABELS } from "@/lib/utils";
import { Users, X } from "lucide-react";

const ROLES = ["ADMIN", "COMPLIANCE", "EMPLOYEE", "AUDITOR"] as const;

const createSchema = z.object({
  email: z.string().email("E-mail inválido"),
  full_name: z.string().min(2, "Nome obrigatório"),
  password: z.string().min(8, "Mínimo 8 caracteres"),
  role: z.enum(ROLES),
  department: z.string().optional(),
});
type CreateForm = z.infer<typeof createSchema>;

const editSchema = z.object({
  full_name: z.string().min(2).optional(),
  role: z.enum(ROLES).optional(),
  department: z.string().optional(),
});
type EditForm = z.infer<typeof editSchema>;

const ROLE_BADGE: Record<string, string> = {
  ADMIN: "bg-slate-900 text-white ring-slate-900/20",
  COMPLIANCE: "bg-brand-50 text-brand-800 ring-brand-700/20",
  EMPLOYEE: "bg-slate-100 text-slate-700 ring-slate-500/20",
  AUDITOR: "bg-amber-50 text-amber-900 ring-amber-700/20",
};

export default function UsersPage() {
  const { user: me } = useAuth();
  const qc = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [editing, setEditing] = useState<any>(null);
  const [error, setError] = useState("");
  const [deactivateTarget, setDeactivateTarget] = useState<any>(null);

  const { data = [], isLoading } = useQuery({
    queryKey: ["users"],
    queryFn: () => api.get("/users").then((r) => r.data),
  });

  const createForm = useForm<CreateForm>({ resolver: zodResolver(createSchema), defaultValues: { role: "EMPLOYEE" } });
  const editForm = useForm<EditForm>({ resolver: zodResolver(editSchema) });

  const createMutation = useMutation({
    mutationFn: (d: CreateForm) => api.post("/users", d),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["users"] });
      setShowCreate(false);
      createForm.reset();
    },
    onError: (e: any) => setError(e.response?.data?.detail ?? "Erro ao criar usuário"),
  });

  const editMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: EditForm }) => api.patch(`/users/${id}`, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["users"] });
      setEditing(null);
    },
    onError: (e: any) => setError(e.response?.data?.detail ?? "Erro ao atualizar usuário"),
  });

  const deactivateMutation = useMutation({
    mutationFn: (id: number) => api.patch(`/users/${id}/deactivate`),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["users"] }); setDeactivateTarget(null); },
    onError: (e: any) => setError(e.response?.data?.detail ?? "Erro ao desativar usuário"),
  });

  const openEdit = (u: any) => {
    setEditing(u);
    editForm.reset({ full_name: u.full_name, role: u.role, department: u.department ?? "" });
  };

  const active = data.filter((u: any) => u.is_active).length;

  return (
    <div>
      <PageHeader
        title="Usuários"
        subtitle={`${data.length} cadastrados · ${active} ativos`}
        action={
          <button onClick={() => { setShowCreate(true); setError(""); }} className="btn-primary text-sm">
            + Novo usuário
          </button>
        }
      />

      {error && <Alert variant="error" className="mb-4">{error}</Alert>}

      {isLoading ? (
        <div className="card p-4"><SkeletonRows rows={7} /></div>
      ) : data.length === 0 ? (
        <EmptyState message="Nenhum usuário cadastrado." icon={<Users />} />
      ) : (
        <div className="card overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-xs text-slate-500 uppercase tracking-wide">
              <tr>
                <th className="px-4 py-3 text-left">Nome</th>
                <th className="px-4 py-3 text-left">E-mail</th>
                <th className="px-4 py-3 text-left">Papel</th>
                <th className="px-4 py-3 text-left">Departamento</th>
                <th className="px-4 py-3 text-left">Status</th>
                <th className="px-4 py-3 text-right">Ações</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {data.map((u: any) => (
                <tr key={u.id} className={`transition-colors ${u.is_active ? "hover:bg-slate-50" : "opacity-50 bg-slate-50"}`}>
                  <td className="px-4 py-3 font-medium">
                    {u.full_name}
                    {u.id === me?.id && (
                      <span className="ml-2 text-xs bg-brand-100 text-brand-600 px-1.5 py-0.5 rounded-full">você</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-slate-500">{u.email}</td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex rounded-md px-2 py-1 text-xs font-semibold ring-1 ring-inset ${ROLE_BADGE[u.role] ?? "bg-slate-100 text-slate-600"}`}>
                      {ROLE_LABELS[u.role] ?? u.role}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-slate-500">{u.department ?? "—"}</td>
                  <td className="px-4 py-3">
                    <StatusBadge status={u.is_active ? "ACTIVE" : "INACTIVE"} />
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex justify-end gap-2">
                      <button onClick={() => { setError(""); openEdit(u); }}
                        className="text-xs text-brand-600 hover:underline">
                        Editar
                      </button>
                      {u.is_active && u.id !== me?.id && (
                        <button
                          onClick={() => { setError(""); setDeactivateTarget(u); }}
                          className="text-xs text-red-500 hover:underline"
                          disabled={deactivateMutation.isPending}>
                          Desativar
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Modal: criar usuário */}
      {showCreate && (
        <Modal title="Novo usuário" onClose={() => { setShowCreate(false); setError(""); createForm.reset(); }}>
          <form onSubmit={createForm.handleSubmit((d) => { setError(""); createMutation.mutate(d); })}
            className="flex flex-col gap-4">
            {error && <Alert variant="error">{error}</Alert>}
            <Field label="Nome completo" error={createForm.formState.errors.full_name?.message}>
              <input {...createForm.register("full_name")} className="input" placeholder="Maria Silva" />
            </Field>
            <Field label="E-mail" error={createForm.formState.errors.email?.message}>
              <input {...createForm.register("email")} type="email" className="input" placeholder="maria@empresa.com" />
            </Field>
            <Field label="Senha" error={createForm.formState.errors.password?.message}>
              <input {...createForm.register("password")} type="password" className="input" placeholder="mínimo 8 caracteres" />
            </Field>
            <div className="grid grid-cols-2 gap-4">
              <Field label="Papel" error={createForm.formState.errors.role?.message}>
                <select {...createForm.register("role")} className="input">
                  {ROLES.map((r) => <option key={r} value={r}>{ROLE_LABELS[r]}</option>)}
                </select>
              </Field>
              <Field label="Departamento">
                <input {...createForm.register("department")} className="input" placeholder="Ex: Gestão" />
              </Field>
            </div>
            <div className="flex justify-end gap-3 pt-2">
              <button type="button" onClick={() => setShowCreate(false)} className="btn-ghost text-sm">Cancelar</button>
              <button type="submit" disabled={createMutation.isPending} className="btn-primary text-sm flex items-center gap-2">
                {createMutation.isPending && <Spinner className="h-4 w-4 border-white border-t-transparent" />}
                Criar usuário
              </button>
            </div>
          </form>
        </Modal>
      )}

      {/* Modal: editar usuário */}
      {editing && (
        <Modal title={`Editar — ${editing.full_name}`} onClose={() => { setEditing(null); setError(""); }}>
          <form onSubmit={editForm.handleSubmit((d) => { setError(""); editMutation.mutate({ id: editing.id, data: d }); })}
            className="flex flex-col gap-4">
            {error && <Alert variant="error">{error}</Alert>}
            <Field label="Nome completo">
              <input {...editForm.register("full_name")} className="input" />
            </Field>
            <div className="grid grid-cols-2 gap-4">
              <Field label="Papel">
                <select {...editForm.register("role")} className="input">
                  {ROLES.map((r) => <option key={r} value={r}>{ROLE_LABELS[r]}</option>)}
                </select>
              </Field>
              <Field label="Departamento">
                <input {...editForm.register("department")} className="input" />
              </Field>
            </div>
            <div className="flex justify-end gap-3 pt-2">
              <button type="button" onClick={() => setEditing(null)} className="btn-ghost text-sm">Cancelar</button>
              <button type="submit" disabled={editMutation.isPending} className="btn-primary text-sm flex items-center gap-2">
                {editMutation.isPending && <Spinner className="h-4 w-4 border-white border-t-transparent" />}
                Salvar
              </button>
            </div>
          </form>
        </Modal>
      )}
      <ConfirmDialog open={Boolean(deactivateTarget)} title="Desativar usuário" description={`“${deactivateTarget?.full_name ?? ""}” perderá acesso ao sistema. Os registros já existentes serão preservados para auditoria.`} confirmLabel="Desativar usuário" destructive busy={deactivateMutation.isPending} onClose={() => setDeactivateTarget(null)} onConfirm={() => deactivateTarget && deactivateMutation.mutate(deactivateTarget.id)} />
    </div>
  );
}

function Modal({ title, onClose, children }: { title: string; onClose: () => void; children: React.ReactNode }) {
  return (
    <div className="modal-backdrop">
      <div className="modal-panel max-w-md" role="dialog" aria-modal="true" aria-labelledby="user-modal-title">
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100">
          <h2 id="user-modal-title" className="font-semibold text-slate-950">{title}</h2>
          <button onClick={onClose} className="rounded-md p-1.5 text-slate-500 hover:bg-slate-100" aria-label="Fechar">
            <X size={18} />
          </button>
        </div>
        <div className="px-6 py-5">{children}</div>
      </div>
    </div>
  );
}

function Field({ label, error, children }: { label: string; error?: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="label">{label}</span>
      {children}
      {error && <p className="text-xs text-red-600 mt-1">{error}</p>}
    </label>
  );
}
