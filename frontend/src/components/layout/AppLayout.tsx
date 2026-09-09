"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";
import { Skeleton } from "@/components/ui/Skeleton";

export function AppLayout({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();
  const [menuOpen, setMenuOpen] = useState(false);
  useEffect(() => { if (!loading && !user) router.push("/login"); }, [user, loading, router]);
  if (loading) return <div className="flex min-h-screen bg-surface"><div className="hidden w-[272px] bg-brand-950 md:block" /><div className="flex-1 p-6 lg:p-10"><Skeleton className="mb-8 h-16 w-full" /><Skeleton className="h-72 w-full" /></div></div>;
  if (!user) return null;
  return (
    <div className="flex h-screen overflow-hidden bg-surface">
      <Sidebar open={menuOpen} onClose={() => setMenuOpen(false)} />
      <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
        <Topbar onOpenMenu={() => setMenuOpen(true)} />
        <main className="app-main flex-1 overflow-auto px-4 py-6 sm:px-6 lg:px-8 lg:py-8"><div className="mx-auto w-full max-w-[1440px]">{children}</div></main>
      </div>
    </div>
  );
}
