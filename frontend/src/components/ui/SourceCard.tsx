import { BookOpenText, FileText } from "lucide-react";

export interface SourceCardProps {
  document_name: string;
  section_title?: string | null;
  page_number?: number | null;
  excerpt: string;
  score: number;
}

export function SourceCard({ source }: { source: SourceCardProps }) {
  return (
    <article className="rounded-lg border border-slate-200 bg-slate-50/70 p-4">
      <div className="mb-3 flex items-start justify-between gap-4">
        <div className="flex min-w-0 items-start gap-2.5">
          <FileText size={16} className="mt-0.5 shrink-0 text-brand-700" aria-hidden="true" />
          <div className="min-w-0">
            <h4 className="truncate text-sm font-semibold text-slate-900">{source.document_name}</h4>
            {(source.section_title || source.page_number) && (
              <p className="mt-0.5 flex items-center gap-1 text-xs text-slate-500">
                <BookOpenText size={12} aria-hidden="true" />
                {[source.section_title, source.page_number ? `Página ${source.page_number}` : null].filter(Boolean).join(" · ")}
              </p>
            )}
          </div>
        </div>
        <span className="shrink-0 font-mono text-[11px] font-semibold text-slate-500">{Math.round(source.score * 100)}% relevante</span>
      </div>
      <blockquote className="border-l border-slate-300 pl-3 text-sm leading-6 text-slate-600">{source.excerpt}</blockquote>
    </article>
  );
}
