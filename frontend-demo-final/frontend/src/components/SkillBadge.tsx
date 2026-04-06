interface Props { name: string; level?: "junior" | "intermédiaire" | "senior" | "expert"; category?: "tech" | "soft" | "language"; }
const lc: Record<string, string> = { junior: "bg-blue-100 text-blue-700", "intermédiaire": "bg-green-100 text-green-700", senior: "bg-purple-100 text-purple-700", expert: "bg-orange-100 text-orange-700" };
const cd: Record<string, string> = { tech: "bg-indigo-500", soft: "bg-pink-500", language: "bg-amber-500" };
export default function SkillBadge({ name, level, category }: Props) {
  return <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${level ? lc[level] : "bg-gray-100 text-gray-700"}`}>
    {category && <span className={`w-1.5 h-1.5 rounded-full ${cd[category]}`} />}{name}
    {level && <span className="opacity-60 text-[10px] uppercase ml-0.5">{level}</span>}
  </span>;
}
