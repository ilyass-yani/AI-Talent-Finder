"use client";

/**
 * E2 - Page de connexion admin cachee.
 *
 * URL : /admin-login  (non referencee dans la navigation Layout.tsx)
 * Elle poste vers POST /api/auth/login avec les credentials admin.
 * Si le role retourne est "admin", redirige vers /admin/dashboard.
 * Sinon, affiche une erreur (acces refuse).
 *
 * La securite reelle est garantie par les guards JWT role==admin
 * deja presents sur les routes backend /api/admin/*.
 */

import { useState } from "react";
import { useRouter } from "next/navigation";
import { authApi } from "@/services/auth";

export default function AdminLoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const data = await authApi.login({ email, password });
      if (data.user.role !== "admin") {
        localStorage.clear();
        setError("Acces refuse : ce compte n'est pas administrateur.");
        setLoading(false);
        return;
      }
      router.push("/admin/dashboard");
    } catch {
      setError("Identifiants incorrects ou serveur inaccessible.");
      setLoading(false);
    }
  };

  return (
    <div className="relative min-h-screen flex items-center justify-center overflow-hidden bg-slate-950 px-4">
      {/* Glow background */}
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute left-1/2 top-0 h-72 w-72 -translate-x-1/2 rounded-full bg-indigo-600/20 blur-3xl" />
        <div className="absolute bottom-0 right-1/4 h-72 w-72 rounded-full bg-rose-600/15 blur-3xl" />
      </div>

      <div className="relative w-full max-w-sm space-y-6">
        <div className="text-center">
          <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-indigo-600 to-violet-600 text-white shadow-lg shadow-indigo-900/50">
            <span className="text-2xl">🔐</span>
          </div>
          <h1 className="font-display text-2xl font-extrabold text-white">Espace Administrateur</h1>
          <p className="mt-1 text-sm text-slate-400">Connexion réservée aux admins</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5 rounded-2xl border border-white/10 bg-white/[0.04] p-8 shadow-2xl backdrop-blur-xl">
          <div>
            <label htmlFor="admin-email" className="block text-sm font-medium text-gray-300 mb-1">
              Email
            </label>
            <input
              id="admin-email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoComplete="email"
              className="w-full px-4 py-2.5 rounded-lg bg-gray-800 border border-gray-700 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
              placeholder="admin@example.com"
            />
          </div>

          <div>
            <label htmlFor="admin-password" className="block text-sm font-medium text-gray-300 mb-1">
              Mot de passe
            </label>
            <input
              id="admin-password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoComplete="current-password"
              className="w-full px-4 py-2.5 rounded-lg bg-gray-800 border border-gray-700 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
              placeholder="••••••••"
            />
          </div>

          {error && (
            <div role="alert" className="bg-red-900/50 border border-red-700 text-red-300 rounded-lg px-4 py-3 text-sm">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="btn-primary w-full disabled:cursor-not-allowed disabled:opacity-50"
          >
            {loading ? "Connexion..." : "Se connecter"}
          </button>
        </form>

        <p className="text-center text-xs text-gray-600">
          Cette page n&apos;est pas liee dans la navigation publique.
        </p>
      </div>
    </div>
  );
}
