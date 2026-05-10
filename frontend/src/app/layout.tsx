import type { Metadata } from "next";
import Providers from "@/components/Providers";
import "./globals.css";

// FORCE BUILD: 2025-05-10T00:55 UTC - Production deploy with API trailing slash fixes
export const metadata: Metadata = { title:"AI Talent Finder", description:"Plateforme intelligente de recrutement — ESISA TechForge4" };
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr" className="h-full antialiased">
      <head>
        <script src="/runtime-config.js" />
      </head>
      <body className="min-h-full flex flex-col font-sans">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
