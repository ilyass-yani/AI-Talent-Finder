"use client";
import Layout from "@/components/Layout";
import CandidateCard from "@/components/CandidateCard";
import { Heart } from "lucide-react";
const favs = [{ id:"1",fullName:"Ahmed Benali",email:"ahmed@mail.com",skills:[{name:"Python",category:"tech" as const},{name:"React",category:"tech" as const}],score:87,isFavorite:true }];
export default function ShortlistPage() {
  return <Layout><div className="max-w-4xl mx-auto space-y-6">
    <div><h1 className="text-2xl font-bold text-gray-900">Shortlist</h1><p className="text-sm text-gray-500 mt-1">Vos candidats favoris</p></div>
    {favs.length > 0 ? <div className="space-y-3">{favs.map(c => <CandidateCard key={c.id} {...c} onToggleFavorite={() => {}} />)}</div>
      : <div className="text-center py-16"><Heart className="h-12 w-12 text-gray-300 mx-auto mb-3" /><p className="text-gray-500">Aucun favori.</p></div>}
  </div></Layout>;
}
