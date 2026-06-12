import { cn } from "@/lib/utils";
export function Spinner({ className }: { className?: string }) {
  return <div className={cn("animate-spin rounded-full border-2 border-slate-200 border-t-brand-500 h-5 w-5", className)} />;
}