const catColors: Record<string,string> = { tech:"bg-indigo-500", soft:"bg-pink-500", language:"bg-amber-500" };
export default function SkillBadge({ name, category }: { name: string; category?: string }) {
  return <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-700">
    {category && <span className={`w-1.5 h-1.5 rounded-full ${catColors[category]||"bg-gray-400"}`} />}{name}
  </span>;
}
