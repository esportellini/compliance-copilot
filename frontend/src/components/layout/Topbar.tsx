"use client";
import { useAuth } from "@/lib/auth-context";
import { ROLE_LABELS } from "@/lib/utils";

export function Topbar({ title }: { title?: string }) {
  const { user } = useAuth();
  return (
    <div className="h-14 border-b border-slate-200 bg-white flex items-center justify-between px-6 shrink-0">
      <p className="text-sm font-medium text-slate-700">{title ?? ""}</p>
      {user && (
        <div className="flex items-center gap-3">
          <div className="text-right">
            <p className="text-xs font-medium text-slate-800">{user.full_name}</p>
            <p className="text-xs text-slate-400">{ROLE_LABELS[user.role] ?? user.role}</p>
          </div>
          <div className="h-8 w-8 rounded-full bg-brand-100 text-brand-700 flex items-center justify-center text-sm font-semibold">
            {user.full_name.charAt(0).toUpperCase()}
          </div>
        </div>
      )}
    </div>
  );
}