"use client";
import Layout from "@/components/Layout";
import { Users, SlidersHorizontal, GitCompareArrows, Wrench, Upload, MessageCircle } from "lucide-react";
import Link from "next/link";
import { useApi } from "@/hooks/useApi";
import { candidatesApi } from "@/services/candidates";
import { skillsApi } from "@/services/skills";
import { jobsApi } from "@/services/jobs";

export default function DashboardPage() {
  const { data: candidates } = useApi(() => candidatesApi.getCandidates(), []);
  const { data: skills } = useApi(() => skillsApi.getSkills(), []);
  const { data: jobs } = useApi(() => jobsApi.getJobs(), []);

  const stats = [
    { label:"Candidats", value: candidates?.length ?? "—", icon:Users, href:"/candidates", color:"bg-blue-50 text-blue-600" },
    { label:"Compétences", value: skills?.length ?? "—", icon:Wrench, href:"/skills", color:"bg-green-50 text-green-600" },
    { label:"Postes", value: jobs?.length ?? "—", icon:SlidersHorizontal, href:"/jobs", color:"bg-purple-50 text-purple-600" },
    { label:"Matching", value:"→", icon:GitCompareArrows, href:"/matching", color:"bg-orange-50 text-orange-600" },
  ];

  return <Layout><div className="max-w-6xl mx-auto space-y-8">
    <div><h1 className="text-2xl font-bold text-gray-900">Tableau de bord</h1><p className="text-sm text-gray-500 mt-1">Vue d&apos;ensemble — données en temps réel depuis le backend</p></div>
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {stats.map(({label,value,icon:I,href,color}) => <Link key={label} href={href} className="bg-white rounded-xl border border-gray-200 p-5 hover:shadow-md transition-shadow"><div className={`p-2.5 rounded-lg ${color} inline-flex mb-3`}><I className="h-5 w-5" /></div><p className="text-2xl font-bold text-gray-900">{value}</p><p className="text-sm text-gray-500">{label}</p></Link>)}
    </div>
    <div className="bg-white rounded-xl border border-gray-200 p-6">
      <h2 className="text-lg font-semibold text-gray-900 mb-4">Actions rapides</h2>
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <Link href="/candidates/upload" className="flex items-center gap-3 px-4 py-3 rounded-lg border border-gray-200 hover:bg-indigo-50 hover:border-indigo-200 transition-colors"><Upload className="h-5 w-5 text-indigo-600" /><span className="text-sm font-medium text-gray-700">Uploader un CV</span></Link>
        <Link href="/jobs" className="flex items-center gap-3 px-4 py-3 rounded-lg border border-gray-200 hover:bg-indigo-50 hover:border-indigo-200 transition-colors"><SlidersHorizontal className="h-5 w-5 text-indigo-600" /><span className="text-sm font-medium text-gray-700">Créer des critères</span></Link>
        <Link href="/chatbot" className="flex items-center gap-3 px-4 py-3 rounded-lg border border-gray-200 hover:bg-indigo-50 hover:border-indigo-200 transition-colors"><MessageCircle className="h-5 w-5 text-indigo-600" /><span className="text-sm font-medium text-gray-700">Chatbot IA</span></Link>
      </div>
    </div>
  </div></Layout>;
}
