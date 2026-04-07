"use client";
import Link from "next/link";
import { Heart, Mail, ExternalLink, Code2 } from "lucide-react";
import SkillBadge from "./SkillBadge";
import ScoreGauge from "./ScoreGauge";
interface Skill { name: string; level?: "junior" | "intermédiaire" | "senior" | "expert"; category?: "tech" | "soft" | "language"; }
interface Props { id: string; fullName: string; email?: string; linkedinUrl?: string; githubUrl?: string; skills: Skill[]; score?: number; isFavorite?: boolean; onToggleFavorite?: (id: string) => void; }
export default function CandidateCard({ id, fullName, email, linkedinUrl, githubUrl, skills, score, isFavorite = false, onToggleFavorite }: Props) {
  return <div className="bg-white rounded-xl border border-gray-200 p-5 hover:shadow-md transition-shadow">
    <div className="flex items-start justify-between mb-3">
      <div>
        <Link href={`/candidates/${id}`} className="text-base font-semibold text-gray-900 hover:text-indigo-600 transition-colors">{fullName}</Link>
        <div className="flex items-center gap-3 mt-1 text-gray-400">
          {email && <a href={`mailto:${email}`} title={email}><Mail className="h-4 w-4 hover:text-gray-600" /></a>}
          {linkedinUrl && <a href={linkedinUrl} target="_blank" rel="noopener noreferrer"><ExternalLink className="h-4 w-4 hover:text-blue-600" /></a>}
          {githubUrl && <a href={githubUrl} target="_blank" rel="noopener noreferrer"><Code2 className="h-4 w-4 hover:text-gray-800" /></a>}
        </div>
      </div>
      <div className="flex items-center gap-3">
        {score !== undefined && <ScoreGauge score={score} size="sm" />}
        {onToggleFavorite && <button onClick={() => onToggleFavorite(id)} className="p-1 rounded-full hover:bg-red-50 transition-colors">
          <Heart className={`h-5 w-5 ${isFavorite ? "fill-red-500 text-red-500" : "text-gray-300 hover:text-red-400"}`} />
        </button>}
      </div>
    </div>
    <div className="flex flex-wrap gap-1.5">
      {skills.slice(0, 6).map(s => <SkillBadge key={s.name} {...s} />)}
      {skills.length > 6 && <span className="text-xs text-gray-400 self-center">+{skills.length - 6}</span>}
    </div>
  </div>;
}
