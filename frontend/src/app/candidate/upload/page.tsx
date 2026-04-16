'use client';

import React, { useState, useRef } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { candidatesApi } from '@/services/candidates';
import { getErrorMessage } from '@/utils/errorHandler';

export default function UploadCV() {
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [dragActive, setDragActive] = useState(false);

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const droppedFile = e.dataTransfer.files[0];
      if (droppedFile.type === 'application/pdf' || droppedFile.name.endsWith('.pdf')) {
        setFile(droppedFile);
        setMessage(null);
      } else {
        setMessage({ type: 'error', text: 'Veuillez télécharger un fichier PDF' });
      }
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selectedFile = e.target.files[0];
      if (selectedFile.type === 'application/pdf' || selectedFile.name.endsWith('.pdf')) {
        setFile(selectedFile);
        setMessage(null);
      } else {
        setMessage({ type: 'error', text: 'Veuillez télécharger un fichier PDF' });
      }
    }
  };

  const handleUpload = async () => {
    if (!file) {
      setMessage({ type: 'error', text: 'Veuillez sélectionner un fichier' });
      return;
    }

    setLoading(true);
    try {
      const response = await candidatesApi.uploadCV(file);
      setMessage({
        type: 'success',
        text: '✓ CV uploadé avec succès! L\'IA analyse ton profil...'
      });

      setTimeout(() => {
        router.push('/candidate/profile');
      }, 2000);
    } catch (error: any) {
      setMessage({
        type: 'error',
        text: getErrorMessage(error)
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-50">
      {/* Navbar */}
      <nav className="bg-white shadow-sm border-b sticky top-0 z-40">
        <div className="max-w-6xl mx-auto px-4 py-4 flex justify-between items-center">
          <Link 
            href="/candidate/dashboard" 
            className="text-gray-600 hover:text-gray-900 font-medium flex items-center gap-2 hover:bg-gray-100 px-3 py-2 rounded-lg transition-all"
          >
            ← Retour au dashboard
          </Link>
          <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-600 to-blue-700 bg-clip-text text-transparent">
            📄 Upload CV
          </h1>
          <div></div>
        </div>
      </nav>

      {/* Main Content */}
      <div className="max-w-4xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="bg-white rounded-xl shadow-md p-8 mb-8 border-l-4 border-blue-500">
          <h2 className="text-3xl font-bold text-gray-900 mb-2">Télécharge ton CV 📥</h2>
          <p className="text-gray-600 text-lg">
            Notre IA analysera ton CV et extraira automatiquement tes compétences, expériences et formations
          </p>
        </div>

        <div className="bg-white rounded-xl shadow-md p-8">
          {/* Upload Area */}
          <div
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
            className={`border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-all duration-300 ${
              dragActive
                ? 'border-blue-500 bg-blue-50 scale-105'
                : 'border-gray-300 hover:border-blue-400 hover:bg-blue-50'
            }`}
            role="region"
            aria-label="Zone de dépôt de fichier"
          >
            <div className="text-6xl mb-4 animate-bounce">📥</div>
            <h3 className="text-2xl font-bold text-gray-900 mb-2">Glisse ton CV ici</h3>
            <p className="text-gray-600 mb-1">ou clique pour sélectionner un fichier</p>
            <p className="text-sm text-gray-500 mb-6">Format supporté: PDF (max 10MB)</p>
            
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf"
              onChange={handleFileChange}
              className="hidden"
              id="file-input"
              aria-label="Sélectionner un fichier PDF"
            />
            <label
              htmlFor="file-input"
              className="inline-block bg-gradient-to-r from-blue-600 to-blue-700 text-white px-8 py-3 rounded-lg hover:from-blue-700 hover:to-blue-800 cursor-pointer font-semibold transition-all transform hover:scale-105 active:scale-95"
            >
              Parcourir les fichiers
            </label>
          </div>

          {/* Selected File */}
          {file && (
            <div className="mt-8 p-6 bg-gradient-to-r from-green-50 to-emerald-50 border-2 border-green-300 rounded-xl animate-fadeIn">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className="text-4xl">✓</div>
                  <div>
                    <p className="font-bold text-gray-900 text-lg">{file.name}</p>
                    <p className="text-sm text-gray-600">
                      Taille: {(file.size / 1024 / 1024).toFixed(2)} MB
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => {
                    setFile(null);
                    if (fileInputRef.current) fileInputRef.current.value = '';
                  }}
                  className="text-red-600 hover:text-red-700 hover:bg-red-50 rounded-lg p-2 transition-colors font-bold"
                  aria-label="Supprimer le fichier"
                >
                  ✕
                </button>
              </div>
            </div>
          )}

          {/* Message */}
          {message && (
            <div
              className={`mt-6 p-4 rounded-xl border-l-4 animation-fadeIn ${
                message.type === 'success'
                  ? 'bg-green-50 border-l-green-500 text-green-800'
                  : 'bg-red-50 border-l-red-500 text-red-800'
              }`}
              role="alert"
              aria-live="assertive"
            >
              {message.text}
            </div>
          )}

          {/* Actions */}
          <div className="mt-8 flex gap-4 justify-between">
            <button
              onClick={() => router.push('/candidate/dashboard')}
              className="px-6 py-3 border-2 border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 font-semibold transition-colors"
              type="button"
            >
              Annuler
            </button>
            <button
              onClick={handleUpload}
              disabled={!file || loading}
              className={`px-8 py-3 rounded-lg font-semibold text-white transition-all transform disabled:opacity-50 disabled:cursor-not-allowed ${
                loading
                  ? 'bg-blue-500'
                  : 'bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 active:scale-95'
              }`}
              type="button"
              aria-label={loading ? 'Upload en cours' : 'Télécharger le CV'}
            >
              {loading ? (
                <span className="flex items-center gap-2">
                  <span className="inline-block animate-spin">⏳</span>
                  Upload en cours...
                </span>
              ) : (
                '✓ Upload CV'
              )}
            </button>
          </div>

          {/* Info Box */}
          <div className="mt-12 p-6 bg-gradient-to-br from-blue-50 to-indigo-50 border-l-4 border-blue-500 rounded-xl">
            <h3 className="font-bold text-gray-900 mb-3 text-lg">💡 Conseils pour meiller résultats</h3>
            <ul className="text-sm text-gray-700 space-y-3">
              <li className="flex items-start gap-2">
                <span className="text-blue-600 font-bold">✓</span>
                <span>Assure-toi que ton CV est clair et bien formaté</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-blue-600 font-bold">✓</span>
                <span>Inclus toutes tes compétences techniques et soft skills</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-blue-600 font-bold">✓</span>
                <span>Mentionne tes expériences professionnelles relevantes</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-blue-600 font-bold">✓</span>
                <span>N'oublie pas tes formations et certifications</span>
              </li>
            </ul>
          </div>

          {/* Privacy Notice */}
          <div className="mt-6 p-4 bg-gray-100 rounded-lg text-sm text-gray-600">
            🔒 Tes données sont sécurisées et chiffrées. Nous ne les partagerons jamais sans ta permission.
          </div>
        </div>
      </div>

      <style jsx>{`
        @keyframes fadeIn {
          from {
            opacity: 0;
            transform: translateY(-10px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
        .animate-fadeIn {
          animation: fadeIn 0.3s ease-out;
        }
      `}</style>
    </div>
  );
}
