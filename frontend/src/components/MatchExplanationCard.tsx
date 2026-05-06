/**
 * MatchExplanationCard — Phase 2 UI Component
 * Displays human-readable match justification for recruiter decision-making
 */

import React, { useEffect, useState } from 'react';
import { ExplainabilityResponse } from '@/services/explainability';

interface MatchExplanationCardProps {
  explanation: ExplainabilityResponse;
  isLoading?: boolean;
  error?: string;
}

export const MatchExplanationCard: React.FC<MatchExplanationCardProps> = ({
  explanation,
  isLoading = false,
  error,
}) => {
  if (isLoading) {
    return (
      <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm animate-pulse">
        <div className="h-6 bg-gray-200 rounded w-3/4 mb-4"></div>
        <div className="space-y-3">
          <div className="h-4 bg-gray-100 rounded w-full"></div>
          <div className="h-4 bg-gray-100 rounded w-5/6"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-4">
        <p className="text-red-700 font-semibold">⚠️ Could not load explanation</p>
        <p className="text-red-600 text-sm mt-1">{error}</p>
      </div>
    );
  }

  if (!explanation) {
    return null;
  }

  return (
    <div className="rounded-lg border border-gray-200 bg-gradient-to-br from-blue-50 to-indigo-50 p-6 shadow-sm">
      {/* Header with Score */}
      <div className="flex items-start justify-between mb-4">
        <div>
          <h3 className="text-lg font-bold text-gray-900">
            Match Explanation
          </h3>
          <p className="text-gray-600 text-sm mt-1">
            {explanation.candidate_name} → {explanation.job_title}
          </p>
        </div>
        <div className="flex flex-col items-end">
          <div className="text-3xl font-bold text-indigo-600">
            {Math.round(explanation.overall_score * 100)}%
          </div>
          <div className="text-sm font-semibold text-gray-700 mt-1">
            {explanation.interpretation}
          </div>
        </div>
      </div>

      {/* Key Reason */}
      <div className="bg-white rounded-lg p-4 mb-4 border-l-4 border-indigo-500">
        <p className="text-sm font-semibold text-gray-700 mb-1">Key Reason:</p>
        <p className="text-gray-900 font-medium">{explanation.key_reason}</p>
      </div>

      {/* Matching Skills */}
      {explanation.matching_skills.length > 0 && (
        <div className="mb-4">
          <p className="text-sm font-semibold text-gray-700 mb-2">
            ✅ Matching Skills ({explanation.matching_skills.length})
          </p>
          <div className="flex flex-wrap gap-2">
            {explanation.matching_skills.map((skill) => (
              <span
                key={skill}
                className="inline-block bg-green-100 text-green-800 text-xs font-semibold px-3 py-1 rounded-full"
              >
                {skill}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Missing Skills */}
      {explanation.missing_skills.length > 0 && (
        <div className="mb-4">
          <p className="text-sm font-semibold text-gray-700 mb-2">
            ❌ Missing Skills ({explanation.missing_skills.length})
          </p>
          <div className="flex flex-wrap gap-2">
            {explanation.missing_skills.map((skill) => (
              <span
                key={skill}
                className="inline-block bg-red-100 text-red-800 text-xs font-semibold px-3 py-1 rounded-full"
              >
                {skill}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Experience Alignment */}
      <div className="bg-white rounded-lg p-4 mb-4">
        <p className="text-sm font-semibold text-gray-700 mb-1">Experience:</p>
        <p className="text-gray-900">{explanation.experience_alignment}</p>
      </div>

      {/* Recommendations */}
      {explanation.recommendations.length > 0 && (
        <div className="bg-yellow-50 rounded-lg p-4 border border-yellow-200">
          <p className="text-sm font-semibold text-gray-700 mb-2">
            💡 Recommendations
          </p>
          <ul className="space-y-1">
            {explanation.recommendations.map((rec, idx) => (
              <li key={idx} className="text-sm text-gray-800 flex items-start">
                <span className="mr-2">•</span>
                <span>{rec}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};

export default MatchExplanationCard;
