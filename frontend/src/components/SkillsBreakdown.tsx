/**
 * SkillsBreakdown — Visual representation of skill matching
 * Shows matched ✅ vs missing ❌ skills with weights
 */

interface Skill {
  skill: string;
  weight: number;
  present: boolean;
  score?: number;
  contribution?: number;
}

interface SkillsBreakdownProps {
  matchedSkills: Skill[];
  missingSkills: string[];
  coverage: number; // percentage
}

export default function SkillsBreakdown({ 
  matchedSkills, 
  missingSkills, 
  coverage 
}: SkillsBreakdownProps) {
  return (
    <div className="bg-gradient-to-br from-slate-50 to-slate-100 rounded-xl p-6 border border-slate-200">
      {/* Header with Coverage */}
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-xl font-bold text-slate-900">Skills Analysis</h3>
        <div className="text-right">
          <div className="text-3xl font-bold text-blue-600">{coverage.toFixed(0)}%</div>
          <div className="text-xs text-slate-600">Coverage</div>
        </div>
      </div>

      {/* Coverage Bar */}
      <div className="mb-6 bg-white rounded-lg p-3">
        <div className="flex gap-1 h-2 bg-slate-200 rounded-full overflow-hidden">
          <div 
            className="bg-gradient-to-r from-blue-500 to-blue-600 rounded-full transition-all"
            style={{ width: `${coverage}%` }}
          />
        </div>
        <div className="text-xs text-slate-600 mt-2">
          {matchedSkills.length} matched / {matchedSkills.length + missingSkills.length} total required
        </div>
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        {/* Matched Skills */}
        <div>
          <div className="text-sm font-bold text-green-700 mb-3 flex items-center gap-1">
            <span>✅</span> Matched Skills
          </div>
          <div className="space-y-2">
            {matchedSkills.length > 0 ? (
              matchedSkills.map((skill) => (
                <div key={skill.skill} className="bg-white rounded-lg p-3 border-l-4 border-green-500">
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-semibold text-slate-900">{skill.skill}</span>
                    <span className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded-full">
                      Weight: {skill.weight}%
                    </span>
                  </div>
                  {skill.contribution !== undefined && (
                    <div className="text-xs text-slate-600">
                      Contribution: +{(skill.contribution * 100).toFixed(1)}%
                    </div>
                  )}
                </div>
              ))
            ) : (
              <div className="text-sm text-slate-500 italic">No matching skills found</div>
            )}
          </div>
        </div>

        {/* Missing Skills */}
        <div>
          <div className="text-sm font-bold text-red-700 mb-3 flex items-center gap-1">
            <span>❌</span> Missing Skills
          </div>
          <div className="space-y-2">
            {missingSkills.length > 0 ? (
              missingSkills.map((skill) => (
                <div key={skill} className="bg-white rounded-lg p-3 border-l-4 border-red-500">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-slate-900">{skill}</span>
                    <span className="text-xs bg-red-100 text-red-700 px-2 py-1 rounded-full">
                      Required
                    </span>
                  </div>
                </div>
              ))
            ) : (
              <div className="text-sm text-slate-500 italic">No missing skills 🎉</div>
            )}
          </div>
        </div>
      </div>

      {/* Recommendation */}
      <div className="mt-6 pt-6 border-t border-slate-200">
        <div className="text-xs font-semibold text-slate-700 mb-2">💡 Recommendation</div>
        {coverage >= 80 ? (
          <p className="text-sm text-slate-700">
            Strong skill alignment. Candidate is well-qualified for this role.
          </p>
        ) : coverage >= 50 ? (
          <p className="text-sm text-slate-700">
            Good foundation with some gaps. Consider training or mixed team approach.
          </p>
        ) : (
          <p className="text-sm text-slate-700">
            Significant skill gaps. Recommend looking for candidates with more relevant experience.
          </p>
        )}
      </div>
    </div>
  );
}
