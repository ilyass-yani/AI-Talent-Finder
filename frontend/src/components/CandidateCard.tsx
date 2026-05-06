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
    <div className="bg-white rounded-lg border border-gray-200 p-4 hover:shadow-lg transition-shadow">
      {/* Header */}
      <div className="flex justify-between items-start mb-3">
        <div>
          <Link href={`/candidates/${id}`} className="text-lg font-semibold text-gray-900 hover:text-indigo-600">
            {fullName}
          </Link>
          <p className="text-sm text-gray-500">{email}</p>
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
        <Link
          href={`/candidates/${id}`}
          className="flex-1 px-3 py-2 bg-indigo-600 text-white text-sm font-medium rounded hover:bg-indigo-700 transition-colors text-center"
        >
          Voir Détails
        </Link>
        <button className="px-3 py-2 border border-gray-300 text-gray-700 text-sm font-medium rounded hover:bg-gray-50 transition-colors">
          ★
        </button>
      </div>
    </div>
  );
}
