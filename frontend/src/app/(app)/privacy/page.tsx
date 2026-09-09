"use client";
import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { PageHeader } from "@/components/layout/PageHeader";
import { Alert } from "@/components/ui/Alert";
import { Spinner } from "@/components/ui/Spinner";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { Shield, Download, UserX, Trash2, ChevronDown, ChevronUp, CheckCircle2 } from "lucide-react";

function Section({ title, icon, children, defaultOpen = false }: {
  title: string; icon: React.ReactNode; children: React.ReactNode; defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="card overflow-hidden">
      <button onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-5 py-4 hover:bg-slate-50 transition-colors">
        <div className="flex items-center gap-3">
          <span className="text-brand-500">{icon}</span>
          <span className="font-semibold text-slate-800 text-sm">{title}</span>
        </div>
        {open ? <ChevronUp size={16} className="text-slate-400" /> : <ChevronDown size={16} className="text-slate-400" />}
      </button>
      {open && <div className="px-5 pb-5 border-t border-slate-100 pt-4">{children}</div>}
    </div>
  );
}

export default function PrivacyPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === "ADMIN";

  const [userId, setUserId]         = useState("");
  const [exportData, setExportData] = useState<any>(null);
  const [exportError, setExportErr] = useState("");
  const [actionMsg, setActionMsg]   = useState("");
  const [actionError, setActionErr] = useState("");
  const [pendingAction, setPendingAction] = useState<"anonymize" | "retention" | null>(null);

  const { data: info, isLoading } = useQuery({
    queryKey: ["privacy-info"],
    queryFn: () => api.get("/privacy/info").then(r => r.data),
  });

  const exportMutation = useMutation({
    mutationFn: () => api.get(`/privacy/user-data/${userId}`).then(r => r.data),
    onSuccess: d => { setExportData(d); setExportErr(""); },
    onError: (e: any) => setExportErr(e.response?.data?.detail ?? "Usuário não encontrado"),
  });

  const anonymizeMutation = useMutation({
    mutationFn: () => api.post(`/privacy/anonymize-user/${userId}`),
    onSuccess: () => { setActionMsg("Usuário anonimizado com sucesso."); setActionErr(""); setPendingAction(null); },
    onError: (e: any) => setActionErr(e.response?.data?.detail ?? "Erro ao anonimizar"),
  });

  const retentionMutation = useMutation({
    mutationFn: () => api.post("/privacy/run-retention-policy").then(r => r.data),
    onSuccess: d => { setActionMsg(`Política executada. ${d.deleted_audit_logs} logs removidos (cutoff: ${d.cutoff_date}).`); setPendingAction(null); },
    onError: (e: any) => setActionErr(e.response?.data?.detail ?? "Erro"),
  });

  if (isLoading) return <div className="flex justify-center py-20"><Spinner className="h-8 w-8" /></div>;

  return (
    <div className="max-w-5xl space-y-5">
      <PageHeader title="Privacidade e LGPD"
        subtitle="Lei Geral de Proteção de Dados — Lei 13.709/2018" />

      {/* princípios */}
      <Section title="Princípios do tratamento de dados" icon={<Shield size={18} />} defaultOpen>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {info?.principios_lgpd?.map((p: any) => (
            <div key={p.nome} className="bg-slate-50 rounded-lg p-3">
              <p className="text-xs font-semibold text-brand-700 mb-1">{p.nome}</p>
              <p className="text-xs text-slate-600">{p.descricao}</p>
            </div>
          ))}
        </div>
      </Section>

      {/* dados tratados */}
      <Section title="Dados tratados pelo sistema" icon={<Shield size={18} />}>
        <div className="space-y-4">
          {info?.dados_tratados?.map((d: any) => (
            <div key={d.categoria} className="border border-slate-200 rounded-lg p-4">
              <p className="text-sm font-semibold text-slate-800 mb-2">{d.categoria}</p>
              <div className="space-y-1.5 text-xs">
                <div className="flex gap-2">
                  <span className="w-24 text-slate-500 shrink-0">Campos</span>
                  <span className="text-slate-700">{d.campos.join(", ")}</span>
                </div>
                <div className="flex gap-2">
                  <span className="w-24 text-slate-500 shrink-0">Finalidade</span>
                  <span className="text-slate-700">{d.finalidade}</span>
                </div>
                <div className="flex gap-2">
                  <span className="w-24 text-slate-500 shrink-0">Base legal</span>
                  <span className="text-slate-700">{d.base_legal}</span>
                </div>
                <div className="flex gap-2">
                  <span className="w-24 text-slate-500 shrink-0">Retenção</span>
                  <span className="text-slate-700">{d.retencao}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </Section>

      {/* minimização */}
      <Section title="Checklist de minimização de dados" icon={<CheckCircle2 size={18} />}>
        <div className="space-y-2">
          {info?.minimizacao?.map((item: string, i: number) => (
            <div key={i} className="flex items-start gap-2.5">
              <CheckCircle2 size={15} className="text-emerald-500 shrink-0 mt-0.5" />
              <p className="text-sm text-slate-700">{item}</p>
            </div>
          ))}
        </div>
      </Section>

      {/* ferramentas admin */}
      {isAdmin && (
        <>
          <Section title="Exportar dados do titular (Art. 18 LGPD)" icon={<Download size={18} />}>
            <p className="text-sm text-slate-500 mb-4">
              Exporta todos os dados vinculados a um usuário. Requer ID numérico do usuário.
            </p>
            <div className="flex flex-col gap-3 sm:flex-row">
              <input value={userId} onChange={e => setUserId(e.target.value)}
                className="input w-full sm:w-44" placeholder="ID do usuário" type="number" />
              <button onClick={() => { setExportErr(""); exportMutation.mutate(); }}
                disabled={!userId || exportMutation.isPending}
                className="btn-primary text-sm flex items-center gap-2">
                {exportMutation.isPending && <Spinner className="h-4 w-4 border-white border-t-transparent" />}
                Exportar
              </button>
            </div>
            {exportError && <Alert variant="error" className="mt-3">{exportError}</Alert>}
            {exportData && (
              <div className="mt-4 space-y-2">
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                  {[
                    ["Consultas", exportData.totais.consultas],
                    ["Pré-aprovações", exportData.totais.pre_aprovacoes],
                    ["Eventos de auditoria", exportData.totais.eventos_auditoria],
                  ].map(([label, val]) => (
                    <div key={label as string} className="bg-slate-50 rounded-lg p-3 text-center">
                      <p className="text-2xl font-bold text-slate-800">{val}</p>
                      <p className="text-xs text-slate-500">{label}</p>
                    </div>
                  ))}
                </div>
                <details className="mt-2">
                  <summary className="text-xs text-slate-500 cursor-pointer hover:text-slate-700">
                    Ver dados completos (JSON)
                  </summary>
                  <pre className="mt-2 text-xs bg-slate-50 rounded p-3 overflow-auto max-h-64 border">
                    {JSON.stringify(exportData, null, 2)}
                  </pre>
                </details>
              </div>
            )}
          </Section>

          <Section title="Anonimizar usuário" icon={<UserX size={18} />}>
            <Alert variant="warning" className="mb-4">
              A anonimização é irreversível. O usuário deve estar desativado antes de ser anonimizado.
              Logs de auditoria com fins regulatórios são preservados sem dados pessoais.
            </Alert>
            <div className="flex flex-col gap-3 sm:flex-row">
              <input value={userId} onChange={e => setUserId(e.target.value)}
                className="input w-full sm:w-44" placeholder="ID do usuário" type="number" />
              <button
                onClick={() => {
                  setActionErr(""); setActionMsg(""); setPendingAction("anonymize");
                }}
                disabled={!userId || anonymizeMutation.isPending}
                className="btn-secondary text-sm flex items-center gap-2">
                {anonymizeMutation.isPending && <Spinner className="h-4 w-4 border-white border-t-transparent" />}
                Anonimizar
              </button>
            </div>
            {actionError && <Alert variant="error" className="mt-3">{actionError}</Alert>}
            {actionMsg && <Alert variant="success" className="mt-3">{actionMsg}</Alert>}
          </Section>

          <Section title="Política de retenção de dados" icon={<Trash2 size={18} />}>
            <p className="text-sm text-slate-500 mb-4">
              Remove logs de auditoria não críticos mais antigos que o prazo configurado.
              Eventos de anonimização, bloqueio e decisões de pré-aprovação são preservados.
            </p>
            <button onClick={() => {
              setActionErr(""); setActionMsg(""); setPendingAction("retention");
            }}
              disabled={retentionMutation.isPending}
              className="btn-destructive text-sm flex items-center gap-2">
              {retentionMutation.isPending && <Spinner className="h-4 w-4 border-white border-t-transparent" />}
              Executar política de retenção
            </button>
            {actionError && <Alert variant="error" className="mt-3">{actionError}</Alert>}
            {actionMsg && <Alert variant="success" className="mt-3">{actionMsg}</Alert>}
          </Section>
        </>
      )}

      {!isAdmin && (
        <Alert variant="info">
          Para solicitar exportação ou anonimização dos seus dados, entre em contato com o administrador do sistema.
        </Alert>
      )}

      <ConfirmDialog
        open={pendingAction === "anonymize"}
        title={`Anonimizar usuário ${userId}`}
        description="Esta ação é irreversível. Os dados pessoais serão anonimizados e os registros regulatórios necessários serão preservados."
        confirmLabel="Anonimizar usuário"
        destructive
        busy={anonymizeMutation.isPending}
        onClose={() => setPendingAction(null)}
        onConfirm={() => anonymizeMutation.mutate()}
      />
      <ConfirmDialog
        open={pendingAction === "retention"}
        title="Executar política de retenção"
        description="Logs antigos abrangidos pela política serão removidos. Eventos regulatórios preservados pela política não serão afetados."
        confirmLabel="Executar política"
        destructive
        busy={retentionMutation.isPending}
        onClose={() => setPendingAction(null)}
        onConfirm={() => retentionMutation.mutate()}
      />
    </div>
  );
}
