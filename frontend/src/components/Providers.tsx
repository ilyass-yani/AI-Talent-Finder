"use client";
import { ThemeProvider } from "@/hooks/useTheme";
export default function Providers({ children }: { children: React.ReactNode }) {
  return <ThemeProvider>{children}</ThemeProvider>;
}
