/**
 * MatchResultCard — Complete candidate match result with all explanations
 * Phase 2 UI Component: Displays score, skills, gaps, and recommendations
 */

import React, { useState } from 'react';
import { ChevronDown, ChevronUp, Sparkles, TrendingUp } from 'lucide-react';
import DecisionBadge from './DecisionBadge';
import SkillsBreakdown from './SkillsBreakdown';
import { feedbackApi } from '@/services/feedback';

export interface MatchResult {
  match_result_id: number;
  criteria_id: number;
  candidate_id: number;
  candidate_name: string;
  candidate_email: string;
  score: number;
  coverage: number;
  matched_skills: string[];
  missing_skills: string[];
  skill_breakdown: Array<{
    skill: string;
    weight: number;
    present: boolean;
    score: number;
    contribution: number;
  }>;
  summary: string;
}

interface MatchResultCardProps {
  result: MatchResult;
  onSelect?: (candidateId: number) => void;
  onExplainClick?: (result: MatchResult) => void;
}

function getDecisionType(score: number): 'accepted' | 'review' | 'rejected' {
  if (score >= 80) return 'accepted';
  if (score >= 50) return 'review';
  return 'rejected';
}

export default function MatchResultCard({ 
  result, 
  onSelect, 
  onExplainClick 
}: MatchResultCardProps) {
  const [expanded, setExpanded] = useState(false);
  const [showFeedback, setShowFeedback] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [recruiterDecision, setRecruiterDecision] = useState<'accepted'|'rejected'|'no_action'>('accepted');
  const [overrideScore, setOverrideScore] = useState<string>('');
  const [reason, setReason] = useState<string>('');
  const [toast, setToast] = useState<{type: 'success'|'error'; message: string}|null>(null);
  const decision = getDecisionType(result.score);

  const submitFeedback = async () => {
    setSubmitting(true);
    try {
      const payload = {
        criteria_id: result.criteria_id,
        candidate_id: result.candidate_id,
        model_predicted_score: result.score,
        model_predicted_decision: getDecisionType(result.score) as 'accepted'|'review'|'rejected',
        recruiter_decision: recruiterDecision,
        recruiter_score_override: overrideScore ? Number(overrideScore) : null,
        feedback_reason: reason || null,
      };

      await feedbackApi.recordDecision(payload);
      // optimistic UX: hide form and reset
      setShowFeedback(false);
      setReason('');
      setOverrideScore('');
      setToast({ type: 'success', message: 'Feedback enregistré' });
      setTimeout(() => setToast(null), 3000);
    } catch (err) {
      setToast({ type: 'error', message: "Erreur lors de l'enregistrement du feedback" });
      setTimeout(() => setToast(null), 4000);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="card-premium overflow-hidden p-0">
      {/* Compact Header - Always Visible */}
      <div 
        className="p-6 cursor-pointer hover:bg-slate-50 transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-start justify-between gap-4">
          {/* Candidate Info */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-3 mb-2">
              <div className="w-12 h-12 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white font-bold text-lg">
                {result.candidate_name.charAt(0).toUpperCase()}
              </div>
              <div className="flex-1 min-w-0">
                <h3 className="font-display font-bold text-lg text-slate-900 truncate">{result.candidate_name}</h3>
                <p className="text-sm text-slate-600 truncate">{result.candidate_email}</p>
              </div>
            </div>
          </div>

          {/* Decision Badge + Score */}
          <div className="flex flex-col items-end gap-3">
            <DecisionBadge score={result.score} decision={decision} showLabel={false} />
            {expanded ? <ChevronUp className="text-slate-400" /> : <ChevronDown className="text-slate-400" />}
          </div>
        </div>

        {/* Summary Text */}
        {result.summary && (
          <p className="text-sm text-slate-600 mt-3 pl-15">{result.summary}</p>
        )}
      </div>

      {/* Expanded Details */}
      {expanded && (
        <div className="border-t border-slate-200 bg-gradient-to-b from-slate-50 to-white">
          <div className="p-6 space-y-6">
            {/* Quick Stats */}
            <div className="grid grid-cols-3 gap-4">
              <div className="bg-blue-50 rounded-lg p-3 border border-blue-200">
                <div className="text-2xl font-bold text-blue-700">{result.matched_skills.length}</div>
                <div className="text-xs text-blue-600 font-medium">Skills Matched</div>
              </div>
              <div className="bg-red-50 rounded-lg p-3 border border-red-200">
                <div className="text-2xl font-bold text-red-700">{result.missing_skills.length}</div>
                <div className="text-xs text-red-600 font-medium">Skills Missing</div>
              </div>
              <div className="bg-green-50 rounded-lg p-3 border border-green-200">
                <div className="text-2xl font-bold text-green-700">{result.coverage.toFixed(0)}%</div>
                <div className="text-xs text-green-600 font-medium">Coverage</div>
              </div>
            </div>

            {/* Skills Breakdown */}
            <div>
              <SkillsBreakdown 
                matchedSkills={result.skill_breakdown.filter(s => s.present)}
                missingSkills={result.missing_skills}
                coverage={result.coverage}
              />
            </div>

            {/* Action Buttons */}
            <div className="flex gap-3">
              <button onClick={() => onExplainClick?.(result)} className="btn-primary flex-1">
                <Sparkles size={18} />
                Explain This Score
              </button>
              <button
                onClick={() => onSelect?.(result.candidate_id)}
                className="flex-1 px-4 py-3 bg-slate-200 text-slate-900 font-semibold rounded-lg hover:bg-slate-300 transition-all flex items-center justify-center gap-2"
              >
                <TrendingUp size={18} />
                View Full Profile
              </button>
              <button
                onClick={() => setShowFeedback(s => !s)}
                className="px-4 py-3 bg-amber-50 text-amber-800 font-semibold rounded-lg hover:bg-amber-100 transition-all flex items-center justify-center gap-2"
              >
                Feedback
              </button>
            </div>

            {/* Decision Recommendation */}
            <div className={`p-4 rounded-lg border-l-4 ${
              decision === 'accepted' ? 'bg-green-50 border-green-500' :
              decision === 'review' ? 'bg-yellow-50 border-yellow-500' :
              'bg-red-50 border-red-500'
            }`}>
              <div className="text-sm font-semibold text-slate-900 mb-1">
                {decision === 'accepted' ? '✅ Recommendation: Schedule Interview' :
                 decision === 'review' ? '🟡 Recommendation: Technical Assessment First' :
                 '❌ Recommendation: Continue Search'}
              </div>
              <p className="text-xs text-slate-700">
                {decision === 'accepted' 
                  ? `${result.candidate_name} demonstrates strong alignment with requirements and is ready for the next hiring stage.`
                  : decision === 'review'
                  ? `${result.candidate_name} shows potential but requires deeper technical assessment to verify skill level and fit.`
                  : `While ${result.candidate_name} has some relevant experience, the gaps suggest continuing the search for a better match.`
                }
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Inline Feedback Form */}
      {expanded && showFeedback && (
        <div className="p-6 border-t border-slate-100 bg-white">
          <div className="space-y-3 max-w-xl">
            <div className="flex items-center gap-3">
              <label className="text-sm font-medium">Décision recruteur</label>
              <select
                value={recruiterDecision}
                onChange={(e) => setRecruiterDecision(e.target.value as any)}
                className="ml-2 p-2 border rounded"
              >
                <option value="accepted">accepted</option>
                <option value="rejected">rejected</option>
                <option value="no_action">no_action</option>
              </select>
            </div>

            <div>
              <label className="text-sm font-medium">Score override (optionnel)</label>
              <input
                type="number"
                value={overrideScore}
                onChange={(e) => setOverrideScore(e.target.value)}
                placeholder="85"
                className="mt-1 w-40 p-2 border rounded"
              />
            </div>

            <div>
              <label className="text-sm font-medium">Raison (optionnel)</label>
              <textarea
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                placeholder="Pourquoi la décision recruteur diffère du score modèle ?"
                className="mt-1 w-full p-2 border rounded"
              />
            </div>

            <div className="flex gap-3">
              <button
                onClick={submitFeedback}
                disabled={submitting}
                className="px-4 py-2 bg-green-600 text-white rounded font-semibold hover:bg-green-700 disabled:opacity-50"
              >
                {submitting ? 'Enregistrement...' : 'Enregistrer le feedback'}
              </button>
              <button
                onClick={() => setShowFeedback(false)}
                className="px-4 py-2 bg-slate-200 rounded hover:bg-slate-300"
              >
                Annuler
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Toast */}
      {toast && (
        <div className={`fixed right-6 bottom-6 z-50 max-w-xs p-3 rounded shadow-lg ${toast.type === 'success' ? 'bg-green-600 text-white' : 'bg-red-600 text-white'}`}>
          {toast.message}
        </div>
      )}
    </div>
  );
}
