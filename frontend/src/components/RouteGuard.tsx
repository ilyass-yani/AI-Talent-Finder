"use client";
import { useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";

const publicRoutes = ["/login", "/register", "/forgot-password"];

export default function RouteGuard({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const isPublic = publicRoutes.some(r => pathname.startsWith(r));

  useEffect(() => {
    if (loading) return;
    if (!user && !isPublic) { router.replace("/login"); return; }
    if (user && isPublic) { router.replace(user.role === "candidate" ? "/candidate/dashboard" : "/dashboard"); return; }
    if (user?.role === "candidate" && !pathname.startsWith("/candidate") && !pathname.startsWith("/settings") && !isPublic && pathname !== "/") { router.replace("/candidate/dashboard"); return; }
    if (user?.role === "recruiter" && pathname.startsWith("/candidate")) { router.replace("/dashboard"); return; }
  }, [user, loading, pathname, isPublic, router]);

  if (loading) return <div className="min-h-screen flex items-center justify-center"><div className="animate-spin h-8 w-8 border-4 border-indigo-600 border-t-transparent rounded-full" /></div>;
  if (!user && !isPublic) return null;
  return <>{children}</>;
}
