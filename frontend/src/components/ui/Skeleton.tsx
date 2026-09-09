import { cn } from "@/lib/utils";
export function Skeleton({ className }: { className?: string }) {
  return <div aria-hidden="true" className={cn("animate-pulse rounded-md bg-slate-200/80", className)} />;
}

export function SkeletonRows({ rows = 6 }: { rows?: number }) {
  return <div className="space-y-3" aria-label="Carregando conteúdo" role="status">{Array.from({ length: rows }).map((_, index) => <div key={index} className="grid grid-cols-[1.6fr_1fr_0.7fr] gap-4 border-b border-slate-100 pb-3"><Skeleton className="h-4" /><Skeleton className="h-4" /><Skeleton className="h-4" /></div>)}</div>;
}
