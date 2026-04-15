'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { Upload } from 'lucide-react';
import CandidateCard from '@/components/CandidateCard';
import { candidatesApi } from '@/services/candidates';
import type { Candidate } from '@/services/candidates';

export default function CandidatesPage() {
  const [candidates, setCandidates] = useState<Candidate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadCandidates = async () => {
      try {
        setLoading(true);
        setError(null);
        const res = await candidatesApi.getCandidates(0, 100);
        setCandidates(res.data || []);
      } catch (err: any) {
        console.error('Error loading candidates:', err);
        setError(err.response?.data?.detail || 'Erreur lors du chargement des candidats');
      } finally {
        setLoading(false);
      }
    };

    loadCandidates();
  }, []);

  return (
    <div className="min-h-screen bg-gray-50 py-8 px-4">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-4xl font-bold text-gray-900">Candidats</h1>
            <p className="text-gray-600 mt-2">
              {candidates.length} candidat{candidates.length !== 1 ? 's' : ''} trouvé{candidates.length !== 1 ? 's' : ''}
            </p>
          </div>
          <Link
            href="/candidate/upload"
            className="flex items-center gap-2 px-6 py-3 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors font-medium"
          >
            <Upload className="w-5 h-5" />
            Uploader un CV
          </Link>
        </div>

        {/* Loading State */}
        {loading && (
          <div className="flex justify-center py-12">
            <div className="text-gray-500">Chargement des candidats...</div>
          </div>
        )}

        {/* Error State */}
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 p-4 rounded-lg mb-8">
            {error}
          </div>
        )}

        {/* Empty State */}
        {!loading && candidates.length === 0 && (
          <div className="bg-white rounded-lg shadow p-12 text-center">
            <p className="text-gray-600 mb-6">Aucun candidat trouvé</p>
            <Link
              href="/candidate/upload"
              className="inline-flex items-center gap-2 px-6 py-3 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors font-medium"
            >
              <Upload className="w-5 h-5" />
              Ajouter un candidat
            </Link>
          </div>
        )}

        {/* Candidates Grid */}
        {!loading && candidates.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {candidates.map((candidate) => (
              <CandidateCard
                key={candidate.id}
                id={candidate.id}
                fullName={candidate.full_name || `Candidat #${candidate.id}`}
                email={candidate.email || ''}
                phone={candidate.phone}
                linkedinUrl={candidate.linkedin_url}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
