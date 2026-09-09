"use client";
import Link from "next/link";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Bell, CheckCheck } from "lucide-react";
import { api } from "@/lib/api";
import { fmtDateTime } from "@/lib/utils";

export function NotificationPopover() {
  const [open, setOpen] = useState(false); const qc = useQueryClient();
  const { data } = useQuery({ queryKey: ["notifications"], queryFn: () => api.get("/notifications").then(r => r.data), refetchInterval: 60_000 });
  const refresh = () => qc.invalidateQueries({ queryKey: ["notifications"] });
  const mark = useMutation({ mutationFn: (id: number) => api.patch(`/notifications/${id}/read`), onSuccess: refresh });
  const all = useMutation({ mutationFn: () => api.post("/notifications/read-all"), onSuccess: refresh });
  return <div className="relative"><button onClick={() => setOpen(!open)} className="relative rounded-md border border-slate-200 p-2 text-slate-600 hover:bg-slate-50" aria-label="Notificações"><Bell size={18} />{data?.unread_count > 0 && <span className="absolute -right-1 -top-1 min-w-4 rounded-full bg-red-600 px-1 text-center text-[10px] font-bold text-white">{data.unread_count}</span>}</button>{open && <div className="absolute right-0 z-40 mt-2 w-[min(360px,calc(100vw-2rem))] overflow-hidden rounded-xl border border-slate-200 bg-white shadow-xl"><div className="flex items-center justify-between border-b px-4 py-3"><p className="text-sm font-semibold">Notificações</p><button onClick={() => all.mutate()} className="flex items-center gap-1 text-xs font-semibold text-brand-700"><CheckCheck size={13} />Marcar todas</button></div><div className="max-h-96 divide-y overflow-auto">{(data?.items ?? []).length === 0 ? <p className="p-6 text-center text-sm text-slate-500">Nenhuma notificação.</p> : data.items.map((item: any) => <Link key={item.id} href={item.entity === "pre_approval_requests" ? `/pre-approvals/${item.entity_id}` : "#"} onClick={() => { if (!item.read_at) mark.mutate(item.id); setOpen(false); }} className={`block px-4 py-3 hover:bg-slate-50 ${item.read_at ? "" : "bg-brand-50/50"}`}><p className="text-sm font-semibold text-slate-800">{item.title}</p><p className="mt-1 text-xs text-slate-600">{item.body}</p><time className="mt-1 block text-[11px] text-slate-400">{fmtDateTime(item.created_at)}</time></Link>)}</div></div>}</div>;
}
