"use client";
import { createContext, useContext, useEffect, useState, ReactNode } from "react";
type Theme = "light" | "dark";
interface ThemeCtx { theme: Theme; toggleTheme: () => void; }
const ThemeContext = createContext<ThemeCtx>({ theme: "light", toggleTheme: () => {} });

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setTheme] = useState<Theme>("light");
  useEffect(() => {
    const s = localStorage.getItem("theme") as Theme | null;
    const p = s || (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
    setTheme(p);
  }, []);
  useEffect(() => {
    document.documentElement.classList.toggle("dark", theme === "dark");
    localStorage.setItem("theme", theme);
  }, [theme]);
  return <ThemeContext.Provider value={{ theme, toggleTheme: () => setTheme(t => t === "dark" ? "light" : "dark") }}>{children}</ThemeContext.Provider>;
}
export function useTheme() { return useContext(ThemeContext); }
