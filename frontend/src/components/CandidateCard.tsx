"use client";

import Link from "next/link";
import { ExternalLink } from "lucide-react";
import SkillBadge from "./SkillBadge";
import ScoreGauge from "./ScoreGauge";

interface CandidateCardProps {
  id: number;
  fullName: string;
  email: string;
  skills?: { name: string; category?: string }[];
  score?: number;
  phone?: string;
  linkedinUrl?: string;
}


export default function CandidateCard({
  id,
  fullName,
  email,
  skills = [],
  score,
  phone,
  linkedinUrl,
}: CandidateCardProps) {
  return (
    <div className="card-premium card-glow p-5">
      {/* Header */}
      <div className="flex justify-between items-start mb-3 gap-3">
        <div className="flex items-start gap-3 min-w-0">
          <div className="flex h-11 w-11 flex-shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-indigo-500 to-violet-500 text-base font-bold text-white">
            {(fullName || 'C')[0].toUpperCase()}
          </div>
          <div className="min-w-0">
            <Link href={`/candidates/${id}`} className="font-display text-lg font-bold text-gray-900 hover:text-indigo-600">
              {fullName}
            </Link>
            <p className="text-sm text-gray-500 truncate">{email}</p>
          </div>
        </div>
        {score !== undefined && <ScoreGauge score={score} />}
      </div>

      {/* Contact Info */}
      {(phone || linkedinUrl) && (
        <div className="flex gap-3 mb-3 text-sm">
          {phone && <span className="text-gray-600">{phone}</span>}
          {linkedinUrl && (
            <a
              href={linkedinUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="text-indigo-600 hover:text-indigo-700 flex items-center gap-1"
            >
              LinkedIn <ExternalLink className="h-3 w-3" />
            </a>
          )}
        </div>
      )}

      {/* Skills */}
      {skills.length > 0 && (
        <div className="mb-3">
          <p className="text-xs font-semibold text-gray-600 mb-2">Compétences</p>
          <div className="flex flex-wrap gap-2">
            {skills.slice(0, 5).map((skill) => (
              <SkillBadge key={skill.name} name={skill.name} category={skill.category} />
            ))}
            {skills.length > 5 && (
              <span className="text-xs text-gray-500 self-center">+{skills.length - 5}</span>
            )}
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="flex gap-2">
        <Link href={`/candidates/${id}`} className="btn-primary flex-1 !py-2 text-sm">
          Voir Détails
        </Link>
        <button className="rounded-xl border border-gray-300 px-3 py-2 text-sm font-medium text-gray-400 transition hover:border-amber-300 hover:bg-amber-50 hover:text-amber-500">
          ★
        </button>
      </div>
    </div>
  );
}
