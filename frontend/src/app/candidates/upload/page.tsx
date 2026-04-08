"use client";
import { useState, useRef } from "react";
import Layout from "@/components/Layout";
import { candidatesApi } from "@/services/candidates";
import { Upload, CheckCircle2, AlertCircle, FileText, X } from "lucide-react";
import Link from "next/link";

export default function UploadPage() {
  const [file, setFile] = useState<File|null>(null);
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<{success:boolean;message:string;candidateId?:number}|null>(null);
  const ref = useRef<HTMLInputElement>(null);

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true); setResult(null);
    try {
      const formData = new FormData();
      formData.append("file", file);
      if (fullName) formData.append("full_name", fullName);
      if (email) formData.append("email", email);
      const res = await candidatesApi.uploadCV(file, fullName || undefined, email || undefined);
      setResult({ success: true, message: res.data.message || "CV uploadé !", candidateId: res.data.candidate_id });
      setFile(null); setFullName(""); setEmail("");
    } catch (e: unknown) {
      setResult({ success: false, message: e instanceof Error ? e.message : "Erreur lors de l'upload." });
    } finally { setUploading(false); }
  };

  return <Layout><div className="max-w-2xl mx-auto space-y-6">
    <div><h1 className="text-2xl font-bold text-gray-900">Upload CV</h1><p className="text-sm text-gray-500 mt-1">Envoi vers <code className="bg-gray-100 px-1 rounded text-xs">POST /candidates/upload</code></p></div>

    <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <div><label className="block text-sm font-medium text-gray-700 mb-1">Nom complet</label><input type="text" value={fullName} onChange={e=>setFullName(e.target.value)} placeholder="Jean Dupont" className="w-full px-4 py-2.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none" /></div>
        <div><label className="block text-sm font-medium text-gray-700 mb-1">Email</label><input type="email" value={email} onChange={e=>setEmail(e.target.value)} placeholder="jean@exemple.com" className="w-full px-4 py-2.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none" /></div>
      </div>

      <div onClick={()=>ref.current?.click()} className="border-2 border-dashed border-gray-300 rounded-xl p-10 text-center cursor-pointer hover:border-indigo-400 hover:bg-gray-50 transition-colors">
        <Upload className="h-10 w-10 text-gray-400 mx-auto mb-3" />
        <p className="text-sm text-gray-600"><span className="font-medium text-indigo-600">Cliquer pour parcourir</span> ou glisser-déposer</p>
        <p className="text-xs text-gray-400 mt-1">PDF uniquement</p>
        <input ref={ref} type="file" accept=".pdf" className="hidden" onChange={e=>setFile(e.target.files?.[0]||null)} />
      </div>

      {file && <div className="flex items-center gap-3 bg-gray-50 rounded-lg px-4 py-2.5">
        <FileText className="h-5 w-5 text-red-500" />
        <div className="flex-1"><p className="text-sm font-medium text-gray-700">{file.name}</p><p className="text-xs text-gray-400">{(file.size/1024).toFixed(0)} Ko</p></div>
        <button onClick={()=>setFile(null)} className="text-gray-400 hover:text-red-500"><X className="h-4 w-4" /></button>
      </div>}

      <button onClick={handleUpload} disabled={!file||uploading} className="w-full py-2.5 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 transition-colors">
        {uploading ? "Envoi en cours..." : "Uploader le CV"}
      </button>

      {result && <div className={`flex items-center gap-2 text-sm ${result.success?"text-green-600":"text-red-600"}`}>
        {result.success ? <CheckCircle2 className="h-4 w-4" /> : <AlertCircle className="h-4 w-4" />}
        {result.message}
        {result.success && result.candidateId && <Link href={`/candidates/${result.candidateId}`} className="text-indigo-600 hover:underline ml-2">Voir le candidat →</Link>}
      </div>}
    </div>
  </div></Layout>;
}
