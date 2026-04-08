"use client";
import Layout from "@/components/Layout";
import { Heart } from "lucide-react";
export default function ShortlistPage() {
  return <Layout><div className="max-w-4xl mx-auto space-y-6">
    <div><h1 className="text-2xl font-bold text-gray-900">Shortlist</h1><p className="text-sm text-gray-500 mt-1">Mode démo — les favoris seront liés au backend quand les routes /favorites seront implémentées</p></div>
    <div className="text-center py-16"><Heart className="h-12 w-12 text-gray-300 mx-auto mb-3" /><p className="text-gray-500">La fonctionnalité shortlist sera disponible quand le backend implémentera les routes favoris.</p></div>
  </div></Layout>;
}
