"use client";
import { RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar, ResponsiveContainer, Legend, Tooltip } from "recharts";
interface SD { name: string; value: number; }
interface Props { skills: SD[]; title?: string; color?: string; compareData?: { name: string; skills: SD[]; color: string }[]; }
const lv: Record<string, number> = { expert: 100, senior: 80, "intermédiaire": 55, junior: 30 };
export function skillLevelToValue(level?: string) { return level ? (lv[level] ?? 50) : 50; }
export default function SkillRadarChart({ skills, title, color = "#6366f1", compareData }: Props) {
  const data = skills.map(s => {
    const p: Record<string, string|number> = { skill: s.name, candidate: s.value };
    compareData?.forEach((c, i) => { const m = c.skills.find(cs => cs.name === s.name); p[`c${i}`] = m?.value ?? 0; });
    return p;
  });
  return <div>
    {title && <h3 className="text-sm font-semibold text-gray-900 mb-3">{title}</h3>}
    <ResponsiveContainer width="100%" height={320}>
      <RadarChart data={data} cx="50%" cy="50%" outerRadius="72%">
        <PolarGrid stroke="#e5e7eb" /><PolarAngleAxis dataKey="skill" tick={{ fontSize: 11, fill: "#6b7280" }} /><PolarRadiusAxis angle={90} domain={[0, 100]} tick={{ fontSize: 10, fill: "#9ca3af" }} />
        <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8, border: "1px solid #e5e7eb" }} formatter={(v) => [`${v}%`, ""]} />
        <Radar name={title || "Candidat"} dataKey="candidate" stroke={color} fill={color} fillOpacity={0.2} strokeWidth={2} />
        {compareData?.map((c, i) => <Radar key={i} name={c.name} dataKey={`c${i}`} stroke={c.color} fill={c.color} fillOpacity={0.1} strokeWidth={2} strokeDasharray="5 5" />)}
        {compareData && compareData.length > 0 && <Legend wrapperStyle={{ fontSize: 12 }} />}
      </RadarChart>
    </ResponsiveContainer>
  </div>;
}
