"use client";

import { usePathname } from "next/navigation";
import { Menu } from "lucide-react";
import { NotificationPopover } from "@/components/NotificationPopover";

const LABELS: Record<string, string> = {
  dashboard: "Visão geral", copilot: "Copilot", history: "Histórico",
  "pre-approvals": "Pré-aprovações", products: "Produtos", documents: "Documentos",
  rules: "Regras", audit: "Auditoria", reports: "Relatórios", training: "Treinamentos",
  users: "Usuários", privacy: "Privacidade", settings: "Configurações",
};

export function Topbar({ onOpenMenu }: { onOpenMenu: () => void }) {
  const pathname = usePathname();
  const root = pathname.split("/").filter(Boolean)[0] ?? "dashboard";
  return (
    <header className="flex h-[72px] shrink-0 items-center justify-between border-b border-slate-200 bg-white px-4 sm:px-6 lg:px-8">
      <div className="flex items-center gap-3">
        <button onClick={onOpenMenu} className="rounded-md border border-slate-200 p-2 text-slate-600 hover:bg-slate-50 md:hidden" aria-label="Abrir menu"><Menu size={19} /></button>
        <div><p className="text-xs font-medium text-slate-500">Workspace</p><p className="text-sm font-semibold text-slate-900">{LABELS[root] ?? "Compliance Copilot"}</p></div>
      </div>
      <div className="flex items-center gap-3">
        <NotificationPopover />
        <div className="flex items-center gap-2 text-xs font-medium text-slate-500"><span className="h-2 w-2 rounded-full bg-emerald-600" aria-hidden="true" /><span className="hidden sm:inline">Ambiente de demonstração</span><span className="sm:hidden">Demo</span></div>
      </div>
    </header>
  );
}
