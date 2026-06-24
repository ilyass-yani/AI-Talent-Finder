"use client";

import { Upload, Trash2 } from "lucide-react";
import { useState } from "react";
import { showToast } from '@/lib/toast';

interface FileUploadProps {
  onFileUpload?: (file: File) => void;
  maxSize?: number; // in MB
}

export default function FileUpload({ onFileUpload, maxSize = 10 }: FileUploadProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [fileName, setFileName] = useState<string | null>(null);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      handleFile(files[0]);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      handleFile(files[0]);
    }
  };

  const handleFile = (file: File) => {
    if (file.size > maxSize * 1024 * 1024) {
      showToast(`Fichier trop volumineux (max ${maxSize}MB)`, 'error');
      return;
    }
    if (!file.type.includes("pdf")) {
      showToast("Seuls les fichiers PDF sont acceptés", 'error');
      return;
    }
    setFileName(file.name);
    onFileUpload?.(file);
  };

  return (
    <div
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      className={`rounded-2xl border-2 border-dashed p-8 text-center transition-all ${
        isDragging ? "border-indigo-500 bg-indigo-50 scale-[1.01]" : "border-gray-300 hover:border-indigo-400 hover:bg-indigo-50/40"
      }`}
    >
      <div className="mx-auto mb-3 flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-indigo-500 to-violet-500 text-white shadow-lg shadow-indigo-200/50">
        <Upload className="h-7 w-7" />
      </div>
      <h3 className="font-display text-lg font-bold text-gray-900 mb-1">Déposez votre CV ici</h3>
      <p className="text-sm text-gray-500 mb-4">ou</p>
      <label className="cursor-pointer">
        <input type="file" accept=".pdf" onChange={handleFileSelect} className="hidden" />
        <span className="btn-primary inline-flex">
          Parcourir
        </span>
      </label>
      <p className="text-xs text-gray-500 mt-4">PDF jusqu'à {maxSize}MB</p>
      {fileName && (
        <div className="mt-4 flex items-center justify-center gap-2 text-green-600">
          <span className="text-sm">✓ {fileName}</span>
          <button
            onClick={() => setFileName(null)}
            className="text-gray-400 hover:text-gray-600"
          >
            <Trash2 className="h-4 w-4" />
          </button>
        </div>
      )}
    </div>
  );
}
