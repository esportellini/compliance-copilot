"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { cn, ROLE_LABELS } from "@/lib/utils";
import {
  BarChart3, BookOpen, Boxes, ClipboardCheck, FileSearch, FileText,
  Gauge, History, LogOut, MessageSquareText, Scale, Settings, ShieldCheck,
  ShieldEllipsis, Users, X,
} from "lucide-react";

type NavItem = { href: string; label: string; icon: typeof Gauge; roles?: string[]; excludeRoles?: string[] };

const GROUPS: { label: string; items: NavItem[] }[] = [
  { label: "Workspace", items: [
    { href: "/dashboard", label: "Visão geral", icon: Gauge },
    { href: "/copilot", label: "Copilot", icon: MessageSquareText, excludeRoles: ["AUDITOR"] },
    { href: "/history", label: "Histórico", icon: History },
  ] },
  { label: "Compliance", items: [
    { href: "/pre-approvals", label: "Pré-aprovações", icon: ClipboardCheck },
    { href: "/products", label: "Produtos", icon: Boxes },
    { href: "/rules", label: "Regras", icon: Scale },
    { href: "/documents", label: "Documentos", icon: FileText },
  ] },
  { label: "Supervisão", items: [
    { href: "/audit", label: "Auditoria", icon: FileSearch, roles: ["ADMIN", "COMPLIANCE", "AUDITOR"] },
    { href: "/reports", label: "Relatórios", icon: BarChart3, roles: ["ADMIN", "COMPLIANCE", "AUDITOR"] },
  ] },
  { label: "Administração", items: [
    { href: "/users", label: "Usuários", icon: Users, roles: ["ADMIN"] },
    { href: "/training", label: "Treinamentos", icon: BookOpen },
    { href: "/privacy", label: "Privacidade", icon: ShieldEllipsis, roles: ["ADMIN"] },
    { href: "/settings", label: "Configurações", icon: Settings, roles: ["ADMIN", "COMPLIANCE"] },
  ] },
];

export function Sidebar({ open, onClose }: { open: boolean; onClose: () => void }) {
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const permitted = (item: NavItem) =>
    (!item.roles || (user && item.roles.includes(user.role))) &&
    (!item.excludeRoles || !user || !item.excludeRoles.includes(user.role));

  return (
    <>
      {open && <button aria-label="Fechar navegação" className="fixed inset-0 z-40 bg-slate-950/40 md:hidden" onClick={onClose} />}
      <aside className={cn(
        "fixed inset-y-0 left-0 z-50 flex w-[272px] flex-col border-r border-brand-900 bg-brand-950 text-white transition-transform duration-200 md:static md:translate-x-0",
        open ? "translate-x-0" : "-translate-x-full",
      )}>
        <div className="flex h-[72px] items-center justify-between border-b border-white/10 px-5">
          <Link href="/dashboard" onClick={onClose} className="flex items-center gap-3 rounded-md focus-visible:outline-white">
            <span className="flex h-9 w-9 items-center justify-center rounded-lg border border-white/15 bg-white/10">
              <ShieldCheck size={20} strokeWidth={1.8} aria-hidden="true" />
            </span>
            <span>
              <span className="block text-[15px] font-semibold tracking-[-0.01em]">Compliance Copilot</span>
              <span className="mt-0.5 block text-[10px] font-semibold uppercase tracking-[0.14em] text-brand-200">Control workspace</span>
            </span>
          </Link>
          <button className="rounded-md p-2 text-brand-100 hover:bg-white/10 md:hidden" onClick={onClose} aria-label="Fechar menu"><X size={18} /></button>
        </div>
        <nav className="flex-1 space-y-5 overflow-y-auto px-3 py-5" aria-label="Navegação principal">
          {GROUPS.map((group) => {
            const items = group.items.filter(permitted);
            if (!items.length) return null;
            return (
              <div key={group.label}>
                <p className="mb-1.5 px-3 text-[10px] font-semibold uppercase tracking-[0.16em] text-brand-300/80">{group.label}</p>
                <div className="space-y-0.5">
                  {items.map(({ href, label, icon: Icon }) => {
                    const active = pathname === href || (href !== "/dashboard" && pathname.startsWith(`${href}/`));
                    return (
                      <Link key={href} href={href} onClick={onClose} aria-current={active ? "page" : undefined}
                        className={cn("flex min-h-10 items-center gap-3 rounded-md px-3 text-sm font-medium transition-colors", active ? "bg-white text-brand-950 shadow-sm" : "text-brand-100 hover:bg-white/10 hover:text-white")}>
                        <Icon size={17} strokeWidth={1.8} aria-hidden="true" /><span>{label}</span>
                      </Link>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </nav>
        <div className="border-t border-white/10 p-3">
          <div className="mb-1 flex items-center gap-3 rounded-md px-3 py-2.5">
            <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-brand-700 text-xs font-semibold ring-1 ring-white/20">{user?.full_name.charAt(0).toUpperCase()}</span>
            <span className="min-w-0">
              <span className="block truncate text-xs font-semibold">{user?.full_name}</span>
              <span className="mt-0.5 block truncate text-[11px] text-brand-200">{user ? ROLE_LABELS[user.role] ?? user.role : ""}</span>
            </span>
          </div>
          <button onClick={logout} className="flex min-h-10 w-full items-center gap-3 rounded-md px-3 text-sm text-brand-100 hover:bg-white/10 hover:text-white">
            <LogOut size={16} strokeWidth={1.8} aria-hidden="true" /> Sair
          </button>
        </div>
      </aside>
    </>
  );
}
