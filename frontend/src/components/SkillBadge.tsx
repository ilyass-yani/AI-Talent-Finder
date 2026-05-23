const catStyles: Record<string, string> = {
  tech: "bg-indigo-50 text-indigo-700 border-indigo-200",
  soft: "bg-pink-50 text-pink-700 border-pink-200",
  language: "bg-amber-50 text-amber-700 border-amber-200",
};
const catDots: Record<string, string> = { tech: "bg-indigo-500", soft: "bg-pink-500", language: "bg-amber-500" };

export default function SkillBadge({ name, category, weight }: { name: string; category?: string; weight?: number }) {
  const style = category ? catStyles[category] || "bg-gray-100 text-gray-700 border-gray-200" : "bg-gray-100 text-gray-700 border-gray-200";
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${style}`}>
      {category && <span className={`w-1.5 h-1.5 rounded-full ${catDots[category] || "bg-gray-400"}`} />}
      {name}
      {weight !== undefined && <span className="opacity-60 ml-0.5">{weight}%</span>}
    </span>
  );
}
