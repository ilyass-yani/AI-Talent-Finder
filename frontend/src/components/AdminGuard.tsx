"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

/**
 * Client-side guard for admin pages. Redirects non-admin / unauthenticated
 * users away. The backend enforces the real authorization (require_admin);
 * this only improves UX by avoiding flashing protected content.
 */
export default function AdminGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [allowed, setAllowed] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    const role = localStorage.getItem("user_role");
    if (!token) {
      router.replace("/auth/login");
    } else if (role !== "admin") {
      // Send non-admins to their own space.
      router.replace(role === "candidate" ? "/candidate/dashboard" : "/recruiter/dashboard");
    } else {
      setAllowed(true);
    }
  }, [router]);

  if (!allowed) {
    return (
      <div className="flex h-64 items-center justify-center text-gray-500">
        Vérification des autorisations…
      </div>
    );
  }

  return <>{children}</>;
}
