"use client";
import Layout from "@/components/Layout";
import { FileText, FileSpreadsheet, File } from "lucide-react";
const opts = [
  { label:"Export PDF", desc:"Rapport détaillé avec scores", icon:FileText, color:"text-red-500 bg-red-50" },
  { label:"Export CSV", desc:"Données tabulaires", icon:File, color:"text-green-500 bg-green-50" },
  { label:"Export Excel", desc:"Rapport formaté", icon:FileSpreadsheet, color:"text-blue-500 bg-blue-50" },
];
export default function ExportPage() {
  return <Layout><div className="max-w-2xl mx-auto space-y-6">
    <div><h1 className="text-2xl font-bold text-gray-900">Export</h1><p className="text-sm text-gray-500 mt-1">Mode démo — en attente des routes export backend</p></div>
    <div className="space-y-3">{opts.map(({label,desc,icon:I,color}) => <button key={label} onClick={()=>alert("Export sera disponible quand le backend l'implémentera.")} className="w-full bg-white rounded-xl border border-gray-200 p-5 flex items-center gap-4 hover:shadow-md transition-shadow text-left"><div className={`p-3 rounded-lg ${color}`}><I className="h-6 w-6" /></div><div className="flex-1"><p className="font-medium text-gray-900">{label}</p><p className="text-sm text-gray-500">{desc}</p></div></button>)}</div>
  </div></Layout>;
}
