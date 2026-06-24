import type { Metadata } from "next";
import Script from "next/script";
import { Inter, Plus_Jakarta_Sans } from "next/font/google";
import Providers from "@/components/Providers";
import "./globals.css";

// Body copy: Inter — clean, highly legible. Headings: Plus Jakarta Sans —
// geometric, modern, premium. Exposed as CSS variables consumed in globals.css.
const inter = Inter({
  subsets: ["latin"],
  variable: "--font-sans",
  display: "swap",
});
const jakarta = Plus_Jakarta_Sans({
  subsets: ["latin"],
  weight: ["500", "600", "700", "800"],
  variable: "--font-display",
  display: "swap",
});

// FORCE BUILD: 2025-05-10T00:55 UTC - Production deploy with API trailing slash fixes
export const metadata: Metadata = { title:"AI Talent Finder", description:"Plateforme intelligente de recrutement — ESISA TechForge4" };
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr" className={`h-full antialiased ${inter.variable} ${jakarta.variable}`}>
      <head>
        <Script src="/runtime-config.js" strategy="beforeInteractive" />
      </head>
      <body className="min-h-full flex flex-col font-sans">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
