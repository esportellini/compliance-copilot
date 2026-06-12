import { cn } from "@/lib/utils";
const styles = { info:"bg-blue-50 border-blue-200 text-blue-800", warning:"bg-amber-50 border-amber-200 text-amber-800",
  error:"bg-red-50 border-red-200 text-red-800", success:"bg-emerald-50 border-emerald-200 text-emerald-800" };
type Variant = keyof typeof styles;
export function Alert({ variant="info", children, className }: { variant?: Variant; children: React.ReactNode; className?: string }) {
  return <div className={cn("rounded-lg border px-4 py-3 text-sm", styles[variant], className)}>{children}</div>;
}