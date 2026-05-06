import type { Metadata } from "next";
import Providers from "@/components/Providers";
import "./globals.css";
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
