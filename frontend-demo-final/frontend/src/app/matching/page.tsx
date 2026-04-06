"use client";
import Layout from "@/components/Layout";
import CandidateCard from "@/components/CandidateCard";
const results = [
  { id: "1", fullName: "Youssef Amrani", skills: [{ name: "Go", category: "tech" as const },{ name: "Kubernetes", category: "tech" as const },{ name: "AWS", category: "tech" as const }], score: 91 },
  { id: "2", fullName: "Ahmed Benali", skills: [{ name: "Python", category: "tech" as const },{ name: "React", category: "tech" as const },{ name: "Docker", category: "tech" as const }], score: 87 },
  { id: "3", fullName: "Sara El Idrissi", skills: [{ name: "JavaScript", category: "tech" as const },{ name: "Next.js", category: "tech" as const }], score: 72 },
  { id: "4", fullName: "Omar Youssef", skills: [{ name: "Java", category: "tech" as const },{ name: "Spring Boot", category: "tech" as const }], score: 65 },
];
export default function MatchingPage() {
  return <Layout><div className="max-w-4xl mx-auto space-y-6">
    <div><h1 className="text-2xl font-bold text-gray-900">Résultats du matching</h1><p className="text-sm text-gray-500 mt-1">Candidats classés par score de correspondance</p></div>
    <div className="space-y-3">{results.map((c, i) => <div key={c.id} className="flex items-center gap-4"><span className="text-lg font-bold text-gray-300 w-8 text-right">#{i+1}</span><div className="flex-1"><CandidateCard {...c} onToggleFavorite={() => {}} /></div></div>)}</div>
  </div></Layout>;
}
