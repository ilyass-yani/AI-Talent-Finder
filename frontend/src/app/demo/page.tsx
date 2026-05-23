'use client';

import React, { useState, useEffect } from 'react';
import MatchExplanationCard from '@/components/MatchExplanationCard';
import { getMatchExplanation, ExplainabilityResponse, getShortlistSummary, ShortlistSummary } from '@/services/explainability';

export default function DemoPage() {
  const [candidateId, setCandidateId] = useState<number>(1);
  const [jobCriteriaId, setJobCriteriaId] = useState<number>(1);
  const [explanation, setExplanation] = useState<ExplainabilityResponse | null>(null);
  const [shortlistSummary, setShortlistSummary] = useState<ShortlistSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [demonstrationMode, setDemonstrationMode] = useState(true);

  // Demo explanation data (for when backend isn't available)
  const demoExplanation: ExplainabilityResponse = {
    candidate_name: 'Alice Johnson',
    job_title: 'Senior React Developer',
    overall_score: 0.87,
    interpretation: '🟢 Strong Match',
    matching_skills: ['React', 'TypeScript', 'Node.js', 'MongoDB', 'AWS'],
    missing_skills: ['Kubernetes', 'GraphQL'],
    experience_alignment: '✅ Highly experienced (7 years > 5 required)',
    key_reason:
      'Strong technical skills alignment: React, TypeScript, Node.js + 2 more',
    recommendations: [
      'Recommended for interview or technical assessment',
      'Consider candidates with: Kubernetes, GraphQL',
    ],
  };

  const demoShortlistSummary: ShortlistSummary = {
    total_candidates_screened: 24,
    strong_matches: 5,
    moderate_matches: 8,
    top_skills_in_pool: [
      'React',
      'TypeScript',
      'Node.js',
      'AWS',
      'Python',
    ],
    recommendations: [
      '✅ Excellent pool: 5 strong matches. Recommend interviews for all.',
      'Consider 8 moderate matches for technical screening.',
    ],
  };

  const handleGenerateExplanation = async () => {
    setLoading(true);
    try {
      if (demonstrationMode) {
        // Simulate delay
        await new Promise((resolve) => setTimeout(resolve, 500));
        setExplanation(demoExplanation);
      } else {
        const result = await getMatchExplanation(candidateId, jobCriteriaId);
        setExplanation(result);
      }
    } catch (error) {
      console.error('Error:', error);
      // Fall back to demo
      setExplanation(demoExplanation);
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateShortlistSummary = async () => {
    setLoading(true);
    try {
      if (demonstrationMode) {
        await new Promise((resolve) => setTimeout(resolve, 500));
        setShortlistSummary(demoShortlistSummary);
      } else {
        const result = await getShortlistSummary(jobCriteriaId);
        setShortlistSummary(result);
      }
    } catch (error) {
      console.error('Error:', error);
      setShortlistSummary(demoShortlistSummary);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    handleGenerateExplanation();
  }, []);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 to-slate-800 py-12 px-4">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-white mb-2">
            🎯 AI Talent Finder — Phase 2 Demo
          </h1>
          <p className="text-gray-300 text-lg">
            Intelligent CV-Job Matching with LLM Explicability
          </p>
        </div>

        {/* Demo Mode Toggle */}
        <div className="mb-8 bg-white/10 backdrop-blur-md rounded-lg p-6 border border-white/20">
          <div className="flex items-center justify-between mb-4">
            <label className="text-white font-semibold">
              🧪 Demonstration Mode
            </label>
            <button
              onClick={() => setDemonstrationMode(!demonstrationMode)}
              className={`px-4 py-2 rounded-full font-semibold transition-all ${
                demonstrationMode
                  ? 'bg-green-500 text-white'
                  : 'bg-gray-500 text-white'
              }`}
            >
              {demonstrationMode ? 'Demo Data' : 'Live Backend'}
            </button>
          </div>
          <p className="text-gray-300 text-sm">
            {demonstrationMode
              ? '✅ Running with pre-generated demo data for showcase'
              : '⚡ Running with live backend API'}
          </p>
        </div>

        {/* Inputs */}
        <div className="grid md:grid-cols-2 gap-6 mb-8">
          <div className="bg-white/5 backdrop-blur-md rounded-lg p-6 border border-white/20">
            <label className="block text-white font-semibold mb-2">
              Candidate ID
            </label>
            <input
              type="number"
              value={candidateId}
              onChange={(e) => setCandidateId(parseInt(e.target.value))}
              disabled={demonstrationMode}
              className="w-full px-4 py-2 rounded-lg bg-white/10 text-white border border-white/20 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div className="bg-white/5 backdrop-blur-md rounded-lg p-6 border border-white/20">
            <label className="block text-white font-semibold mb-2">
              Job Criteria ID
            </label>
            <input
              type="number"
              value={jobCriteriaId}
              onChange={(e) => setJobCriteriaId(parseInt(e.target.value))}
              disabled={demonstrationMode}
              className="w-full px-4 py-2 rounded-lg bg-white/10 text-white border border-white/20 focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        </div>

        {/* Action Buttons */}
        <div className="grid md:grid-cols-2 gap-4 mb-8">
          <button
            onClick={handleGenerateExplanation}
            disabled={loading}
            className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white font-bold rounded-lg transition-all disabled:opacity-50"
          >
            {loading ? '⏳ Generating Explanation...' : '📊 Get Match Explanation'}
          </button>

          <button
            onClick={handleGenerateShortlistSummary}
            disabled={loading}
            className="px-6 py-3 bg-indigo-600 hover:bg-indigo-700 text-white font-bold rounded-lg transition-all disabled:opacity-50"
          >
            {loading ? '⏳ Generating Summary...' : '📈 Get Shortlist Summary'}
          </button>
        </div>

        {/* Results */}
        <div className="space-y-6">
          {/* Match Explanation */}
          {explanation && (
            <div className="bg-white/5 backdrop-blur-md rounded-lg p-6 border border-white/20">
              <h2 className="text-white text-xl font-bold mb-4">
                📋 Match Explanation
              </h2>
              <MatchExplanationCard
                explanation={explanation}
                isLoading={loading}
              />
            </div>
          )}

          {/* Shortlist Summary */}
          {shortlistSummary && (
            <div className="bg-white/5 backdrop-blur-md rounded-lg p-6 border border-white/20">
              <h2 className="text-white text-xl font-bold mb-4">
                📊 Shortlist Summary
              </h2>
              <div className="bg-white/5 rounded-lg p-6 space-y-4">
                <div className="grid md:grid-cols-3 gap-4">
                  <div className="bg-gradient-to-br from-green-400/20 to-green-600/20 rounded-lg p-4">
                    <p className="text-green-300 text-sm">Strong Matches</p>
                    <p className="text-white text-3xl font-bold">
                      {shortlistSummary.strong_matches}
                    </p>
                  </div>
                  <div className="bg-gradient-to-br from-yellow-400/20 to-yellow-600/20 rounded-lg p-4">
                    <p className="text-yellow-300 text-sm">Moderate Matches</p>
                    <p className="text-white text-3xl font-bold">
                      {shortlistSummary.moderate_matches}
                    </p>
                  </div>
                  <div className="bg-gradient-to-br from-blue-400/20 to-blue-600/20 rounded-lg p-4">
                    <p className="text-blue-300 text-sm">Total Screened</p>
                    <p className="text-white text-3xl font-bold">
                      {shortlistSummary.total_candidates_screened}
                    </p>
                  </div>
                </div>

                {shortlistSummary.top_skills_in_pool.length > 0 && (
                  <div>
                    <p className="text-white font-semibold mb-2">
                      Top Skills in Pool
                    </p>
                    <div className="flex flex-wrap gap-2">
                      {shortlistSummary.top_skills_in_pool.map((skill) => (
                        <span
                          key={skill}
                          className="bg-blue-500 text-white text-sm font-semibold px-3 py-1 rounded-full"
                        >
                          {skill}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {shortlistSummary.recommendations.length > 0 && (
                  <div>
                    <p className="text-white font-semibold mb-2">
                      💡 Recommendations
                    </p>
                    <ul className="space-y-2">
                      {shortlistSummary.recommendations.map((rec, idx) => (
                        <li
                          key={idx}
                          className="text-gray-300 flex items-start"
                        >
                          <span className="mr-2">•</span>
                          <span>{rec}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="mt-12 text-center text-gray-400">
          <p className="text-sm">
            Phase 2 Features: LLM Explicability + Lightweight Siamese Matching
          </p>
          <p className="text-xs mt-2">
            🚀 Backend API v1.0 — Production Ready
          </p>
        </div>
      </div>
    </div>
  );
}
