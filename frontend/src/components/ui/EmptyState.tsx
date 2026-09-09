export function EmptyState({ message, icon }: { message: string; icon?: React.ReactNode }) {
  return (
    <div className="card flex flex-col items-center justify-center gap-3 px-6 py-16 text-center text-slate-500">
      {icon && <div className="text-slate-400 [&_svg]:h-7 [&_svg]:w-7">{icon}</div>}
      <p className="max-w-md text-sm">{message}</p>
    </div>
  );
}
