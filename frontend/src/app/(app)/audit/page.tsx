"use client";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { PageHeader } from "@/components/layout/PageHeader";
import { Spinner } from "@/components/ui/Spinner";
import { SkeletonRows } from "@/components/ui/Skeleton";
import { EmptyState } from "@/components/ui/EmptyState";
import { fmtDateTime } from "@/lib/utils";
import { ShieldAlert, Download, X } from "lucide-react";

const SEVERITIES = ["INFO","WARNING","CRITICAL"];
const EVENT_TYPES = [
  "LOGIN","LOGIN_FAILED","USER_CREATED","USER_UPDATED","USER_DEACTIVATED","USER_ANONYMIZED",
  "DOCUMENT_UPLOADED","DOCUMENT_PROCESSED","DOCUMENT_ARCHIVED","DOCUMENT_STATUS_CHANGED",
  "COPILOT_QUERY","COPILOT_OUT_OF_SCOPE",
  "PRE_APPROVAL_CREATED","PRE_APPROVAL_DECISION","PRE_APPROVAL_COMMENT",
  "PRODUCT_CREATED","PRODUCT_UPDATED","PRODUCT_DELETED","PRODUCT_RESTRICTED","PRODUCT_BLOCKED","PRODUCT_STATUS_CHANGED",
  "RULE_CREATED","RULE_UPDATED","UNAUTHORIZED_ACCESS","RETENTION_RUN",
];

const SEV_BADGE: Record<string,string> = {
  INFO:     "bg-blue-50 text-blue-700",
  WARNING:  "bg-amber-50 text-amber-700",
  CRITICAL: "bg-red-100 text-red-700 font-semibold",
};

function DetailModal({ event, onClose }: { event: any; onClose: () => void }) {
  return (
    <div className="modal-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
      <div className="modal-panel max-w-xl" role="dialog" aria-modal="true" aria-labelledby="audit-detail-title">
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100">
          <div><p className="text-[10px] font-semibold uppercase tracking-[0.1em] text-slate-500">Evento de auditoria #{event.id}</p><h2 id="audit-detail-title" className="mt-1 font-mono text-sm font-semibold text-slate-950">{event.event_type}</h2></div>
          <button onClick={onClose} className="rounded-md p-1.5 text-slate-500 hover:bg-slate-100" aria-label="Fechar detalhe"><X size={18} /></button>
        </div>
        <div className="px-6 py-5 space-y-3 text-sm">
          <Row label="Data" value={fmtDateTime(event.created_at)} />
          <Row label="Ator" value={event.actor_label ?? "—"} />
          <Row label="Entidade" value={event.entity ? `${event.entity} #${event.entity_id}` : "—"} />
          <Row label="Severidade" value={event.severity} />
          <Row label="Mensagem" value={event.message} />
          {event.meta && Object.keys(event.meta).length > 0 && (
            <div>
              <span className="text-xs text-slate-500 block mb-1">Metadados</span>
              <pre className="text-xs bg-slate-50 rounded p-3 overflow-auto max-h-48 border text-slate-700">
                {JSON.stringify(event.meta, null, 2)}
              </pre>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex gap-3">
      <span className="w-24 text-xs text-slate-500 shrink-0 pt-0.5">{label}</span>
      <span className="text-slate-800 break-all">{value}</span>
    </div>
  );
}

export default function AuditPage() {
  const [eventTypeF, setEventType] = useState("");
  const [severityF, setSeverity]   = useState("");
  const [dateFrom, setDateFrom]    = useState("");
  const [dateTo, setDateTo]        = useState("");
  const [selected, setSelected]    = useState<any>(null);

  const params = new URLSearchParams();
  if (eventTypeF) params.set("event_type", eventTypeF);
  if (severityF)  params.set("severity", severityF);
  if (dateFrom)   params.set("date_from", dateFrom);
  if (dateTo)     params.set("date_to", dateTo);
  params.set("limit", "300");

  const { data = [], isLoading } = useQuery({
    queryKey: ["audit", eventTypeF, severityF, dateFrom, dateTo],
    queryFn: () => api.get(`/audit-logs?${params}`).then((r) => r.data),
  });

  const hasFilters = eventTypeF || severityF || dateFrom || dateTo;
  const clearFilters = () => { setEventType(""); setSeverity(""); setDateFrom(""); setDateTo(""); };

  const exportCSV = () => {
    const csvParams = new URLSearchParams(params);
    window.open(`${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api"}/audit-logs/export/csv?${csvParams}`);
  };

  return (
    <div>
      <PageHeader
        title="Trilha de Auditoria"
        subtitle={`${data.length} evento${data.length !== 1 ? "s" : ""}`}
        action={
          <button onClick={exportCSV}
            className="flex items-center gap-2 text-sm border border-slate-200 hover:bg-slate-50 px-3 py-2 rounded-lg transition-colors">
            <Download size={14} /> Exportar CSV
          </button>
        }
      />

      <div className="mb-5 flex flex-wrap gap-3 rounded-lg border border-slate-200 bg-white p-3">
        <select value={eventTypeF} onChange={(e) => setEventType(e.target.value)} className="input w-56">
          <option value="">Tipo de evento</option>
          {EVENT_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
        </select>
        <select value={severityF} onChange={(e) => setSeverity(e.target.value)} className="input w-36">
          <option value="">Severidade</option>
          {SEVERITIES.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
        <input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} className="input w-40" />
        <input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} className="input w-40" />
        {hasFilters && (
          <button onClick={clearFilters}
            className="flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-700 px-3 py-2 rounded-lg hover:bg-slate-100">
            <X size={14} /> Limpar
          </button>
        )}
      </div>

      {isLoading ? (
        <div className="card p-4"><SkeletonRows rows={8} /></div>
      ) : data.length === 0 ? (
        <EmptyState message="Nenhum evento encontrado." icon={<ShieldAlert />} />
      ) : (
        <div className="card overflow-x-auto">
          <table className="w-full text-xs">
            <thead className="bg-slate-50 text-slate-500 uppercase tracking-wide">
              <tr>
                <th className="px-4 py-3 text-left">Data</th>
                <th className="px-4 py-3 text-left">Evento</th>
                <th className="px-4 py-3 text-left">Ator</th>
                <th className="px-4 py-3 text-left">Entidade</th>
                <th className="px-4 py-3 text-left">Sev.</th>
                <th className="px-4 py-3 text-left">Mensagem</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {data.map((e: any) => (
                <tr key={e.id} tabIndex={0} role="button"
                  onClick={() => setSelected(e)}
                  onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); setSelected(e); } }}
                  className="hover:bg-slate-50 transition-colors cursor-pointer">
                  <td className="px-4 py-2 whitespace-nowrap text-slate-400">{fmtDateTime(e.created_at)}</td>
                  <td className="px-4 py-2 font-mono font-medium text-slate-700">{e.event_type}</td>
                  <td className="px-4 py-2 text-slate-500 truncate max-w-[140px]">{e.actor_label ?? "—"}</td>
                  <td className="px-4 py-2 text-slate-500">
                    {e.entity ? `${e.entity} #${e.entity_id}` : "—"}
                  </td>
                  <td className="px-4 py-2">
                    <span className={`px-2 py-0.5 rounded-full ${SEV_BADGE[e.severity] ?? ""}`}>{e.severity}</span>
                  </td>
                  <td className="px-4 py-2 text-slate-600 truncate max-w-xs">{e.message}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {selected && <DetailModal event={selected} onClose={() => setSelected(null)} />}
    </div>
  );
}
