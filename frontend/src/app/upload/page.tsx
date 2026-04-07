"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";
export default function UploadRedirect() {
  const { user, loading } = useAuth(); const router = useRouter();
  useEffect(() => { if (!loading) router.replace(user?.role === "candidate" ? "/candidate/upload" : "/dashboard"); }, [user, loading, router]);
  return <div className="min-h-screen flex items-center justify-center"><div className="animate-spin h-8 w-8 border-4 border-indigo-600 border-t-transparent rounded-full" /></div>;
}
