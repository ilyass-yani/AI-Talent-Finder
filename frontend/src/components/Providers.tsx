"use client";
import { AuthProvider } from "@/hooks/useAuth";
import { ThemeProvider } from "@/hooks/useTheme";
import RouteGuard from "@/components/RouteGuard";
export default function Providers({ children }: { children: React.ReactNode }) {
  return <ThemeProvider><AuthProvider><RouteGuard>{children}</RouteGuard></AuthProvider></ThemeProvider>;
}
