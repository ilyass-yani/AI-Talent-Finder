"use client";

import React, { useState } from "react";
import { Download, FileText, Sheet, File, AlertCircle } from "lucide-react";

interface ExportOption {
  id: string;
  name: string;
  icon: React.ReactNode;
  format: string;
  color: string;
  description: string;
}

interface ExportSettings {
  includeScores: boolean;
  includeSkills: boolean;
  includeExperience: boolean;
  includeEducation: boolean;
  sortBy: "score" | "name" | "date";
}

export default function ExportPage() {
  const [selectedFormat, setSelectedFormat] = useState<string>("");
  const [settings, setSettings] = useState<ExportSettings>({
    includeScores: true,
    includeSkills: true,
    includeExperience: true,
    includeEducation: true,
    sortBy: "score"
  });
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const exportOptions: ExportOption[] = [
    {
      id: "csv",
      name: "CSV",
      icon: <Sheet className="w-8 h-8" />,
      format: "text/csv",
      color: "from-green-500 to-emerald-600",
      description: "Format tabulaire - Importer dans Excel/Google Sheets"
    },
    {
      id: "excel",
      name: "Excel",
      icon: <File className="w-8 h-8" />,
      format: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      color: "from-lime-500 to-green-600",
      description: "Formaté avec formules - Filtrage & tri automatiques"
    },
    {
      id: "pdf",
      name: "PDF",
      icon: <FileText className="w-8 h-8" />,
      format: "application/pdf",
      color: "from-red-500 to-rose-600",
      description: "Rapport professionnel - Prêt à partager"
    }
  ];

  const handleExport = async () => {
    if (!selectedFormat) {
      setMessage({ type: "error", text: "Sélectionnez un format d'export" });
      return;
    }

    setLoading(true);
    setMessage(null);

    try {
      const token = localStorage.getItem("access_token");
      const response = await fetch(`http://localhost:8000/api/export/${selectedFormat}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify(settings)
      });

      if (!response.ok) throw new Error("Export failed");

      // Download file
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `candidates-export-${new Date().toISOString().split("T")[0]}.${selectedFormat}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      setMessage({ type: "success", text: `✅ Export ${selectedFormat.toUpperCase()} réussi!` });
    } catch (error) {
      console.error("Export error:", error);
      setMessage({ type: "error", text: "❌ Erreur lors de l'export. Réessayez." });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-50 to-gray-100 p-6">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
            <Download className="w-8 h-8 text-indigo-600" />
            Exporter les Résultats
          </h1>
          <p className="text-gray-600 mt-2">
            Téléchargez les candidats et les résultats de matching dans le format de votre choix
          </p>
        </div>

        {/* Messages */}
        {message && (
          <div
            className={`mb-6 p-4 rounded-lg flex items-start gap-3 ${
              message.type === "success"
                ? "bg-green-50 border border-green-200 text-green-800"
                : "bg-red-50 border border-red-200 text-red-800"
            }`}
          >
            <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
            <span>{message.text}</span>
          </div>
        )}

        {/* Export Options */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
          {exportOptions.map(option => (
            <button
              key={option.id}
              onClick={() => setSelectedFormat(option.id)}
              className={`p-6 rounded-lg border-2 transition-all ${
                selectedFormat === option.id
                  ? "border-indigo-600 bg-indigo-50 shadow-lg"
                  : "border-gray-200 bg-white hover:border-gray-300"
              }`}
            >
              <div className={`w-12 h-12 rounded-lg bg-gradient-to-br ${option.color} text-white flex items-center justify-center mb-4`}>
                {option.icon}
              </div>
              <h3 className="font-bold text-lg text-gray-900">{option.name}</h3>
              <p className="text-sm text-gray-600 mt-2">{option.description}</p>
              {selectedFormat === option.id && (
                <div className="mt-3 text-indigo-600 font-semibold flex items-center gap-2">
                  ✓ Sélectionné
                </div>
              )}
            </button>
          ))}
        </div>

        {/* Settings */}
        <div className="bg-white rounded-lg p-6 border border-gray-200 mb-6">
          <h2 className="text-lg font-bold text-gray-900 mb-4">Options d'export</h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
            {/* Include Options */}
            <div className="space-y-3">
              <label className="flex items-center gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={settings.includeScores}
                  onChange={e =>
                    setSettings({ ...settings, includeScores: e.target.checked })
                  }
                  className="w-4 h-4 rounded border-gray-300 text-indigo-600"
                />
                <span className="text-gray-700">Inclure les scores de matching</span>
              </label>
              <label className="flex items-center gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={settings.includeSkills}
                  onChange={e =>
                    setSettings({ ...settings, includeSkills: e.target.checked })
                  }
                  className="w-4 h-4 rounded border-gray-300 text-indigo-600"
                />
                <span className="text-gray-700">Inclure les compétences</span>
              </label>
              <label className="flex items-center gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={settings.includeExperience}
                  onChange={e =>
                    setSettings({ ...settings, includeExperience: e.target.checked })
                  }
                  className="w-4 h-4 rounded border-gray-300 text-indigo-600"
                />
                <span className="text-gray-700">Inclure l'expérience</span>
              </label>
              <label className="flex items-center gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={settings.includeEducation}
                  onChange={e =>
                    setSettings({ ...settings, includeEducation: e.target.checked })
                  }
                  className="w-4 h-4 rounded border-gray-300 text-indigo-600"
                />
                <span className="text-gray-700">Inclure l'éducation</span>
              </label>
            </div>

            {/* Sort Option */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Trier par
              </label>
              <select
                value={settings.sortBy}
                onChange={e =>
                  setSettings({
                    ...settings,
                    sortBy: e.target.value as "score" | "name" | "date"
                  })
                }
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="score">Score de matching (décroissant)</option>
                <option value="name">Nom (A-Z)</option>
                <option value="date">Date d'ajout (récent)</option>
              </select>
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex gap-4">
          <button
            onClick={handleExport}
            disabled={loading || !selectedFormat}
            className="flex-1 bg-indigo-600 hover:bg-indigo-700 disabled:bg-gray-400 text-white py-3 rounded-lg font-semibold flex items-center justify-center gap-2 transition"
          >
            {loading ? (
              <>
                <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                Export en cours...
              </>
            ) : (
              <>
                <Download className="w-5 h-5" />
                Exporter maintenant
              </>
            )}
          </button>
          <button
            onClick={() => window.history.back()}
            className="px-6 py-3 border border-gray-300 rounded-lg font-semibold text-gray-700 hover:bg-gray-50 transition"
          >
            Retour
          </button>
        </div>

        {/* Info Box */}
        <div className="mt-8 p-4 bg-blue-50 border border-blue-200 rounded-lg">
          <p className="text-sm text-blue-800">
            <strong>📝 Note:</strong> L'export inclura tous les candidats avec leurs informations sélectionnées ci-dessus.
            Les fichiers seront téléchargés sur votre ordinateur.
          </p>
        </div>
      </div>
    </div>
  );
}
