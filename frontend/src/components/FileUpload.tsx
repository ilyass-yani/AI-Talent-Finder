"use client";

import { Upload, Trash2 } from "lucide-react";
import { useState } from "react";

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
      alert(`Fichier trop volumineux (max ${maxSize}MB)`);
      return;
    }
    if (!file.type.includes("pdf")) {
      alert("Seuls les fichiers PDF sont acceptés");
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
      className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
        isDragging ? "border-indigo-500 bg-indigo-50" : "border-gray-300 hover:border-gray-400"
      }`}
    >
      <Upload className="h-12 w-12 mx-auto text-gray-400 mb-3" />
      <h3 className="text-lg font-semibold text-gray-900 mb-1">Déposez votre CV ici</h3>
      <p className="text-sm text-gray-500 mb-4">ou</p>
      <label className="cursor-pointer">
        <input type="file" accept=".pdf" onChange={handleFileSelect} className="hidden" />
        <span className="inline-block px-4 py-2 bg-indigo-600 text-white font-medium rounded hover:bg-indigo-700">
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
