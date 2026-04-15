'use client';

import React from 'react';
import { useParams } from 'next/navigation';
import CandidateDetail from '@/components/CandidateDetail';

export default function CandidatePage() {
  const params = useParams();
  const candidateId = parseInt(params.id as string, 10);

  if (isNaN(candidateId)) {
    return (
      <div className="min-h-screen bg-gray-50 p-6">
        <div className="text-red-600">ID de candidat invalide</div>
      </div>
    );
  }

  return <CandidateDetail candidateId={candidateId} />;
}
