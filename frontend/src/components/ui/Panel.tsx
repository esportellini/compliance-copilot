import { cn } from "@/lib/utils";

export function Panel({ children, className }: { children: React.ReactNode; className?: string }) {
  return <section className={cn("card", className)}>{children}</section>;
}

export function SectionHeader({ title, description, action }: { title: string; description?: string; action?: React.ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-4 border-b border-slate-200 px-5 py-4">
      <div><h2 className="section-title">{title}</h2>{description && <p className="section-description">{description}</p>}</div>
      {action && <div className="shrink-0">{action}</div>}
    </div>
  );
}

export function TableFrame({ children, className }: { children: React.ReactNode; className?: string }) {
  return <div className={cn("card overflow-x-auto", className)}>{children}</div>;
}

export function FilterBar({ children }: { children: React.ReactNode }) {
  return <div className="mb-5 flex flex-wrap items-center gap-3 rounded-lg border border-slate-200 bg-white p-3 shadow-sm">{children}</div>;
}
