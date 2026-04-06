"use client";
import { useState, useEffect, createContext, useContext, ReactNode } from "react";
import { useRouter } from "next/navigation";

const DEMO_MODE = true;
export type UserRole = "recruiter" | "candidate";
interface User { id: string; email: string; full_name: string; role: UserRole; }
interface AuthCtx {
  user: User | null; loading: boolean;
  login: (email: string, password: string, role: UserRole) => Promise<void>;
  register: (email: string, password: string, fullName: string, role: UserRole) => Promise<void>;
  logout: () => void;
  isRecruiter: boolean; isCandidate: boolean;
}

const AuthContext = createContext<AuthCtx | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    if (DEMO_MODE) {
      const s = typeof window !== "undefined" ? sessionStorage.getItem("demo_user") : null;
      if (s) setUser(JSON.parse(s));
    }
    setLoading(false);
  }, []);

  const save = (u: User) => { setUser(u); sessionStorage.setItem("demo_user", JSON.stringify(u)); };

  const login = async (email: string, _pw: string, role: UserRole) => {
    if (DEMO_MODE) {
      await new Promise(r => setTimeout(r, 500));
      save({ id: "demo-1", email, full_name: email.split("@")[0].replace(/[._]/g, " "), role });
      router.push(role === "candidate" ? "/candidate/dashboard" : "/dashboard");
    }
  };

  const register = async (email: string, _pw: string, fullName: string, role: UserRole) => {
    if (DEMO_MODE) {
      await new Promise(r => setTimeout(r, 500));
      save({ id: "demo-1", email, full_name: fullName, role });
      router.push(role === "candidate" ? "/candidate/dashboard" : "/dashboard");
    }
  };

  const logout = () => { setUser(null); sessionStorage.removeItem("demo_user"); router.push("/login"); };

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout, isRecruiter: user?.role === "recruiter", isCandidate: user?.role === "candidate" }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
