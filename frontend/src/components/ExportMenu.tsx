"use client";
import { Download } from "lucide-react";
import { api } from "@/lib/api";

export function ExportMenu({ requestId }: { requestId: string | number }) {
  const download = async (format: "pdf" | "json") => {
    const response = await api.get(`/pre-approvals/${requestId}/audit-package.${format}`, { responseType: "blob" });
    const url = URL.createObjectURL(response.data);
    const link = document.createElement("a"); link.href = url; link.download = `pre-approval-${requestId}-audit-package.${format}`; link.click(); URL.revokeObjectURL(url);
  };
  return <div className="flex flex-wrap gap-2" aria-label="Exportar audit package"><button className="btn-secondary text-sm" onClick={() => download("pdf")}><Download size={14} />PDF</button><button className="btn-ghost border border-slate-200 text-sm" onClick={() => download("json")}><Download size={14} />JSON</button></div>;
}
