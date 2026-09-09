"use client";

import { AlertTriangle, X } from "lucide-react";
import { Button } from "./Button";

export function ConfirmDialog({ open, title, description, confirmLabel, destructive = false, busy = false, onConfirm, onClose }: {
  open: boolean; title: string; description: string; confirmLabel: string; destructive?: boolean; busy?: boolean; onConfirm: () => void; onClose: () => void;
}) {
  if (!open) return null;
  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
      <div className="modal-panel" role="alertdialog" aria-modal="true" aria-labelledby="confirm-title" aria-describedby="confirm-description">
        <div className="flex items-start justify-between gap-4 border-b border-slate-200 px-5 py-4">
          <div className="flex items-start gap-3"><AlertTriangle className={destructive ? "text-red-700" : "text-amber-700"} size={20} aria-hidden="true" /><div><h2 id="confirm-title" className="text-base font-semibold text-slate-950">{title}</h2><p id="confirm-description" className="mt-1 text-sm leading-6 text-slate-600">{description}</p></div></div>
          <button className="rounded-md p-1.5 text-slate-500 hover:bg-slate-100" onClick={onClose} aria-label="Fechar confirmação"><X size={17} /></button>
        </div>
        <div className="flex justify-end gap-3 px-5 py-4"><Button variant="secondary" onClick={onClose} disabled={busy}>Cancelar</Button><Button variant={destructive ? "destructive" : "primary"} onClick={onConfirm} disabled={busy}>{busy ? "Processando…" : confirmLabel}</Button></div>
      </div>
    </div>
  );
}
