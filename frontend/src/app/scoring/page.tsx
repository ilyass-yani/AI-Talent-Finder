"use client";

import { useState } from "react";
import axios from "axios";

interface MatchDecision {
  decision: string;
  score: number;
  skill_match_ratio: number;
  experience_gap_years: number;
  missing_skills: string[];
  explanation: string;
}

interface TestDataset {
  n_candidates: number;
  n_jobs: number;
  candidates: any[];
  jobs: any[];
}

export default function ScoringPage() {
  const [testDataset, setTestDataset] = useState<TestDataset | null>(null);
  const [selectedCandidate, setSelectedCandidate] = useState<any>(null);
  const [selectedJob, setSelectedJob] = useState<any>(null);
  const [matchResult, setMatchResult] = useState<MatchDecision | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadTestDataset = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await axios.get("/api/matching/test-dataset?n_candidates=5&n_jobs=3");
      setTestDataset(response.data);
      if (response.data.candidates.length > 0) {
        setSelectedCandidate(response.data.candidates[0]);
      }
      if (response.data.jobs.length > 0) {
        setSelectedJob(response.data.jobs[0]);
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message);
    }
    setLoading(false);
  };

  const computeScore = async () => {
    if (!selectedCandidate || !selectedJob) {
      setError("Please select a candidate and a job");
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const response = await axios.post("/api/matching/advanced-score", {
        cv_skills: selectedCandidate.normalized_skills || [],
        job_skills: selectedJob.required_skills || [],
        cv_years: selectedCandidate.experience_years || 0,
        job_years: selectedJob.required_years || 0,
        cv_education: 2,
        job_education: 2,
        semantic_similarity: 0.7,
      });
      setMatchResult(response.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message);
    }
    setLoading(false);
  };

  const getDecisionColor = (decision: string) => {
    if (decision === "accepted") return "bg-green-100 border-green-500";
    if (decision === "to_review") return "bg-yellow-100 border-yellow-500";
    return "bg-red-100 border-red-500";
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 p-8">
      <div className="max-w-6xl mx-auto">
        <h1 className="text-4xl font-bold text-gray-800 mb-2">Advanced Scoring Demo</h1>
        <p className="text-gray-600 mb-8">
          Test the intelligent CV-Job matching system with calibrated business rules
        </p>

        {/* Load Test Dataset Button */}
        <div className="bg-white rounded-lg shadow-md p-6 mb-8">
          <button
            onClick={loadTestDataset}
            disabled={loading}
            className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 transition"
          >
            {loading && testDataset === null ? "Loading..." : "Load Test Dataset"}
          </button>
        </div>

        {error && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-8">
            {error}
          </div>
        )}

        {testDataset && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
            {/* Candidates Column */}
            <div className="bg-white rounded-lg shadow-md p-6">
              <h2 className="text-2xl font-bold mb-4 text-gray-800">Candidates</h2>
              <div className="space-y-2 max-h-72 overflow-y-auto">
                {testDataset.candidates.map((cand, idx) => (
                  <button
                    key={idx}
                    onClick={() => setSelectedCandidate(cand)}
                    className={`w-full text-left p-4 rounded border-2 transition ${
                      selectedCandidate?.id === cand.id
                        ? "bg-blue-100 border-blue-500"
                        : "bg-gray-50 border-gray-200 hover:bg-gray-100"
                    }`}
                  >
                    <div className="font-semibold text-gray-800">{cand.full_name}</div>
                    <div className="text-sm text-gray-600">{cand.experience_years} years exp</div>
                    <div className="text-xs text-gray-500 mt-1">
                      {cand.normalized_skills?.slice(0, 3).join(", ")}
                    </div>
                  </button>
                ))}
              </div>
            </div>

            {/* Jobs Column */}
            <div className="bg-white rounded-lg shadow-md p-6">
              <h2 className="text-2xl font-bold mb-4 text-gray-800">Jobs</h2>
              <div className="space-y-2 max-h-72 overflow-y-auto">
                {testDataset.jobs.map((job, idx) => (
                  <button
                    key={idx}
                    onClick={() => setSelectedJob(job)}
                    className={`w-full text-left p-4 rounded border-2 transition ${
                      selectedJob?.id === job.id
                        ? "bg-blue-100 border-blue-500"
                        : "bg-gray-50 border-gray-200 hover:bg-gray-100"
                    }`}
                  >
                    <div className="font-semibold text-gray-800">{job.title}</div>
                    <div className="text-sm text-gray-600">{job.company}</div>
                    <div className="text-xs text-gray-500 mt-1">
                      {job.required_skills?.slice(0, 3).join(", ")}
                    </div>
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Match Result */}
        {selectedCandidate && selectedJob && (
          <div className="bg-white rounded-lg shadow-md p-6 mb-8">
            <div className="mb-4 flex justify-between items-center">
              <h3 className="text-xl font-bold text-gray-800">
                {selectedCandidate.full_name} ↔ {selectedJob.title}
              </h3>
              <button
                onClick={computeScore}
                disabled={loading}
                className="px-6 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:bg-gray-400 transition"
              >
                {loading ? "Computing..." : "Compute Score"}
              </button>
            </div>

            {matchResult && (
              <div className={`border-2 rounded-lg p-6 ${getDecisionColor(matchResult.decision)}`}>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                  <div>
                    <div className="text-sm font-semibold text-gray-600">Decision</div>
                    <div className="text-xl font-bold text-gray-800 capitalize">
                      {matchResult.decision.replace("_", " ")}
                    </div>
                  </div>
                  <div>
                    <div className="text-sm font-semibold text-gray-600">Score</div>
                    <div className="text-2xl font-bold text-gray-800">
                      {(matchResult.score * 100).toFixed(1)}%
                    </div>
                  </div>
                  <div>
                    <div className="text-sm font-semibold text-gray-600">Skill Match</div>
                    <div className="text-2xl font-bold text-gray-800">
                      {(matchResult.skill_match_ratio * 100).toFixed(0)}%
                    </div>
                  </div>
                  <div>
                    <div className="text-sm font-semibold text-gray-600">Experience Gap</div>
                    <div className="text-2xl font-bold text-gray-800">
                      {matchResult.experience_gap_years} years
                    </div>
                  </div>
                </div>

                <div className="bg-white rounded p-4 mb-4">
                  <div className="whitespace-pre-wrap text-gray-700 text-sm leading-relaxed">
                    {matchResult.explanation}
                  </div>
                </div>

                {matchResult.missing_skills.length > 0 && (
                  <div className="mt-4 pt-4 border-t border-gray-300">
                    <div className="text-sm font-semibold text-gray-700 mb-2">Missing Skills:</div>
                    <div className="flex flex-wrap gap-2">
                      {matchResult.missing_skills.map((skill, idx) => (
                        <span
                          key={idx}
                          className="px-3 py-1 bg-white border border-gray-400 rounded-full text-sm"
                        >
                          {skill}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
