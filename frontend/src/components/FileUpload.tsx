"use client";
import { useState, useRef, DragEvent } from "react";
import { Upload, FileText, X, CheckCircle2, AlertCircle } from "lucide-react";
interface Props { onUpload: (files: File[]) => Promise<void>; maxSizeMB?: number; }
export default function FileUpload({ onUpload, maxSizeMB = 5 }: Props) {
  const [files, setFiles] = useState<File[]>([]);
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [status, setStatus] = useState<"idle"|"success"|"error">("idle");
  const ref = useRef<HTMLInputElement>(null);
  const add = (fl: FileList | File[]) => {
    const v: File[] = [];
    Array.from(fl).forEach(f => { if (f.name.toLowerCase().endsWith(".pdf") && f.size <= maxSizeMB*1024*1024 && !files.find(e => e.name === f.name)) v.push(f); });
    setFiles(p => [...p, ...v]); setStatus("idle");
  };
  const upload = async () => { if (!files.length) return; setUploading(true); try { await onUpload(files); setStatus("success"); setFiles([]); } catch { setStatus("error"); } finally { setUploading(false); } };
  return <div className="space-y-4">
    <div onDragOver={e => { e.preventDefault(); setDragging(true); }} onDragLeave={() => setDragging(false)}
      onDrop={(e: DragEvent) => { e.preventDefault(); setDragging(false); add(e.dataTransfer.files); }}
      onClick={() => ref.current?.click()}
      className={`border-2 border-dashed rounded-xl p-10 text-center cursor-pointer transition-colors ${dragging ? "border-indigo-500 bg-indigo-50" : "border-gray-300 hover:border-indigo-400 hover:bg-gray-50"}`}>
      <Upload className="h-10 w-10 text-gray-400 mx-auto mb-3" />
      <p className="text-sm text-gray-600"><span className="font-medium text-indigo-600">Cliquer pour parcourir</span> ou glisser-déposer vos CV</p>
      <p className="text-xs text-gray-400 mt-1">PDF uniquement, max {maxSizeMB} Mo</p>
      <input ref={ref} type="file" accept=".pdf" multiple className="hidden" onChange={e => e.target.files && add(e.target.files)} />
    </div>
    {files.length > 0 && <div className="space-y-2">
      {files.map(f => <div key={f.name} className="flex items-center gap-3 bg-gray-50 rounded-lg px-4 py-2.5">
        <FileText className="h-5 w-5 text-red-500 flex-shrink-0" />
        <div className="flex-1 min-w-0"><p className="text-sm font-medium text-gray-700 truncate">{f.name}</p><p className="text-xs text-gray-400">{(f.size/1024).toFixed(0)} Ko</p></div>
        <button onClick={() => setFiles(p => p.filter(x => x.name !== f.name))} className="text-gray-400 hover:text-red-500"><X className="h-4 w-4" /></button>
      </div>)}
      <button onClick={upload} disabled={uploading} className="w-full py-2.5 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 transition-colors">
        {uploading ? "Envoi en cours..." : `Envoyer ${files.length} fichier(s)`}
      </button>
    </div>}
    {status === "success" && <div className="flex items-center gap-2 text-green-600 text-sm"><CheckCircle2 className="h-4 w-4" />CV envoyé(s) avec succès !</div>}
    {status === "error" && <div className="flex items-center gap-2 text-red-600 text-sm"><AlertCircle className="h-4 w-4" />Erreur lors de l&apos;envoi.</div>}
  </div>;
}
