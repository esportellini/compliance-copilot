"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { cn } from "@/lib/utils";
import {
  LayoutDashboard, MessageSquare, History, Package, FileText, Scale,
  ClipboardCheck, BookOpen, Users, Settings, ShieldAlert, LogOut, BarChart2, Lock,
} from "lucide-react";

const NAV = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/copilot", label: "Copilot", icon: MessageSquare },
  { href: "/history", label: "Histórico", icon: History },
  { href: "/pre-approvals", label: "Pré-aprovações", icon: ClipboardCheck },
  { href: "/products", label: "Produtos", icon: Package },
  { href: "/documents", label: "Documentos", icon: FileText },
  { href: "/rules", label: "Regras", icon: Scale },
  { href: "/audit", label: "Auditoria", icon: ShieldAlert, roles: ["ADMIN","COMPLIANCE","AUDITOR"] },
  { href: "/reports", label: "Relatórios", icon: BarChart2, roles: ["ADMIN","COMPLIANCE","AUDITOR"] },
  { href: "/training", label: "Treinamentos", icon: BookOpen },
  { href: "/users", label: "Usuários", icon: Users, roles: ["ADMIN"] },
  { href: "/privacy", label: "Privacidade (LGPD)", icon: Lock, roles: ["ADMIN"] },
  { href: "/settings", label: "Configurações", icon: Settings, roles: ["ADMIN","COMPLIANCE"] },
];

export function Sidebar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const filtered = NAV.filter(n => !n.roles || (user && n.roles.includes(user.role)));

  return (
    <aside className="w-60 min-h-screen bg-brand-900 flex flex-col text-white shrink-0">
      <div className="px-5 py-6 border-b border-brand-700">
        <p className="text-lg font-bold tracking-tight">Compliance Copilot</p>
        <p className="text-xs text-brand-100 mt-0.5 opacity-70">{user?.department ?? ""}</p>
      </div>
      <nav className="flex-1 py-4 px-3 flex flex-col gap-0.5">
        {filtered.map(({ href, label, icon: Icon }) => (
          <Link key={href} href={href}
            className={cn(
              "flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors",
              pathname.startsWith(href) ? "bg-brand-600 text-white" : "text-brand-100 hover:bg-brand-700"
            )}>
            <Icon size={16} />
            {label}
          </Link>
        ))}
      </nav>
      <div className="p-3 border-t border-brand-700">
        <div className="px-3 py-2 mb-1">
          <p className="text-xs font-medium truncate">{user?.full_name}</p>
          <p className="text-xs text-brand-200 opacity-70 truncate">{user?.email}</p>
        </div>
        <button onClick={logout}
          className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-brand-100 hover:bg-brand-700 transition-colors">
          <LogOut size={16} /> Sair
        </button>
      </div>
    </aside>
  );
}