import { cn } from "@/lib/utils";
export function Badge({ className, children }: { className?: string; children: React.ReactNode }) {
  return <span className={cn("inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-xs font-semibold leading-none ring-1 ring-inset", className)}>{children}</span>;
}
