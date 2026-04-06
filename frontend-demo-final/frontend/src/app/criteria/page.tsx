"use client";
import Layout from "@/components/Layout";
import CriteriaForm from "@/components/CriteriaForm";
export default function CriteriaPage() {
  return <Layout><div className="max-w-2xl mx-auto space-y-6">
    <div><h1 className="text-2xl font-bold text-gray-900">Critères de matching</h1><p className="text-sm text-gray-500 mt-1">Définissez les compétences recherchées et leur pondération pour classer les candidats.</p></div>
    <div className="bg-white rounded-xl border border-gray-200 p-6"><CriteriaForm onSubmit={d => console.log("Critères:", d)} /></div>
  </div></Layout>;
}
