"use client";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { PageHeader } from "@/components/layout/PageHeader";
import { Alert } from "@/components/ui/Alert";
import { Spinner } from "@/components/ui/Spinner";
import { Settings, Brain, ShieldCheck, Lock, Scale, ChevronDown, ChevronUp, Save } from "lucide-react";

const SECTION_ICONS: Record<string, React.ReactNode> = {
  ia:         <Brain size={16} />,
  compliance: <ShieldCheck size={16} />,
  seguranca:  <Lock size={16} />,
  lgpd:       <Scale size={16} />,
};

function SettingField({ setting, canEdit, onChange }: {
  setting: any; canEdit: boolean; onChange: (key: string, value: string) => void;
}) {
  const [localVal, setLocalVal] = useState(setting.value ?? "");

  const handleChange = (v: string) => {
    setLocalVal(v);
    onChange(setting.key, v);
  };

  return (
    <div className="flex items-start gap-4 py-3 border-b border-slate-50 last:border-0">
      <div className="flex-1">
        <p className="text-sm font-medium text-slate-800">{setting.label}</p>
        {setting.description && (
          <p className="text-xs text-slate-400 mt-0.5">{setting.description}</p>
        )}
      </div>
      <div className="shrink-0 w-48">
        {!canEdit ? (
          <div className="px-3 py-2 bg-slate-50 rounded-lg text-sm text-slate-600 font-mono">
            {setting.type === "boolean"
              ? (setting.value === "true" ? "✅ Ativo" : "❌ Inativo")
              : setting.value || "—"}
          </div>
        ) : setting.type === "boolean" ? (
          <button
            onClick={() => handleChange(localVal === "true" ? "false" : "true")}
            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
              localVal === "true" ? "bg-brand-500" : "bg-slate-200"
            }`}>
            <span className={`inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform ${
              localVal === "true" ? "translate-x-6" : "translate-x-1"
            }`} />
          </button>
        ) : setting.type === "select" ? (
          <select
            value={localVal}
            onChange={e => handleChange(e.target.value)}
            className="input text-sm">
            {setting.options?.map((o: string) => (
              <option key={o} value={o}>{o}</option>
            ))}
          </select>
        ) : (
          <input
            type={setting.type === "number" ? "number" : "text"}
            value={localVal}
            onChange={e => handleChange(e.target.value)}
            className="input text-sm"
          />
        )}
      </div>
    </div>
  );
}

function SectionCard({ section, canEdit, onSave, isSaving }: {
  section: any; canEdit: boolean;
  onSave: (changes: Record<string, string>) => void;
  isSaving: boolean;
}) {
  const [open, setOpen] = useState(true);
  const [changes, setChanges] = useState<Record<string, string>>({});
  const hasChanges = Object.keys(changes).length > 0;

  const handleChange = (key: string, value: string) => {
    setChanges(prev => ({ ...prev, [key]: value }));
  };

  return (
    <div className="card overflow-hidden">
      <button onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-5 py-4 hover:bg-slate-50 transition-colors">
        <div className="flex items-center gap-3">
          <span className="text-brand-500">{SECTION_ICONS[section.key]}</span>
          <span className="font-semibold text-slate-800 text-sm">{section.label}</span>
          {!canEdit && (
            <span className="text-xs bg-slate-100 text-slate-500 px-2 py-0.5 rounded-full">somente leitura</span>
          )}
        </div>
        {open ? <ChevronUp size={16} className="text-slate-400" /> : <ChevronDown size={16} className="text-slate-400" />}
      </button>
      {open && (
        <div className="px-5 pb-4 border-t border-slate-100">
          {section.settings.map((s: any) => (
            <SettingField
              key={s.key}
              setting={{ ...s, value: changes[s.key] ?? s.value }}
              canEdit={canEdit}
              onChange={handleChange}
            />
          ))}
          {canEdit && hasChanges && (
            <div className="pt-3 flex justify-end">
              <button
                onClick={() => { onSave(changes); setChanges({}); }}
                disabled={isSaving}
                className="btn-primary text-sm flex items-center gap-2">
                {isSaving
                  ? <Spinner className="h-4 w-4 border-white border-t-transparent" />
                  : <Save size={14} />}
                Salvar {Object.keys(changes).length} alteração(ões)
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function SettingsPage() {
  const { user } = useAuth();
  const qc = useQueryClient();
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");

  const { data, isLoading } = useQuery({
    queryKey: ["settings"],
    queryFn: () => api.get("/settings").then(r => r.data),
  });

  const mutation = useMutation({
    mutationFn: async (changes: Record<string, string>) => {
      await Promise.all(
        Object.entries(changes).map(([key, value]) =>
          api.put(`/settings/${key}?value=${encodeURIComponent(value)}`)
        )
      );
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["settings"] });
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    },
    onError: (e: any) => setError(e.response?.data?.detail ?? "Erro ao salvar"),
  });

  if (isLoading) return <div className="flex justify-center py-20"><Spinner className="h-8 w-8" /></div>;

  const isAdmin = user?.role === "ADMIN";

  return (
    <div className="max-w-3xl space-y-5">
      <PageHeader title="Configurações" subtitle="Parâmetros do sistema por seção" />

      {saved && <Alert variant="success">Configurações salvas com sucesso.</Alert>}
      {error && <Alert variant="error">{error}</Alert>}

      {!isAdmin && (
        <Alert variant="info">
          Você tem acesso de leitura às configurações. Somente administradores podem alterar os valores.
        </Alert>
      )}

      {data?.sections?.map((section: any) => (
        <SectionCard
          key={section.key}
          section={section}
          canEdit={section.can_edit}
          onSave={(changes) => { setError(""); mutation.mutate(changes); }}
          isSaving={mutation.isPending}
        />
      ))}
    </div>
  );
}