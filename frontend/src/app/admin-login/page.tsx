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
    <div className="min-h-screen flex items-center justify-center bg-gray-950 px-4">
      <div className="w-full max-w-sm space-y-6">
        <div className="text-center">
          <div className="text-4xl mb-3">🔐</div>
          <h1 className="text-2xl font-bold text-white">Espace Administrateur</h1>
          <p className="text-gray-400 text-sm mt-1">Connexion reservee aux admins</p>
        </div>

        <form onSubmit={handleSubmit} className="bg-gray-900 rounded-xl p-8 space-y-5 shadow-2xl border border-gray-800">
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
            className="w-full py-3 rounded-lg bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold transition-colors"
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
