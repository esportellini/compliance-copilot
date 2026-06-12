export function EmptyState({ message, icon }: { message: string; icon?: React.ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-slate-400 gap-3">
      {icon && <div className="text-4xl">{icon}</div>}
      <p className="text-sm">{message}</p>
    </div>
  );
}