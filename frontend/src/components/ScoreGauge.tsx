interface Props { score: number; size?: "sm" | "md" | "lg"; }
export default function ScoreGauge({ score, size = "md" }: Props) {
  const d = { sm: 48, md: 72, lg: 96 }[size], s = { sm: 4, md: 6, lg: 8 }[size], f = { sm: "text-xs", md: "text-sm", lg: "text-lg" }[size];
  const r = (d - s) / 2, c = 2 * Math.PI * r, o = c - (score / 100) * c;
  const cl = score >= 80 ? "text-green-500" : score >= 50 ? "text-amber-500" : "text-red-500";
  return <div className="relative inline-flex items-center justify-center" style={{ width: d, height: d }}>
    <svg width={d} height={d} className="-rotate-90">
      <circle cx={d/2} cy={d/2} r={r} fill="none" stroke="currentColor" strokeWidth={s} className="text-gray-200" />
      <circle cx={d/2} cy={d/2} r={r} fill="none" stroke="currentColor" strokeWidth={s} strokeDasharray={c} strokeDashoffset={o} strokeLinecap="round" className={`${cl} transition-all duration-700`} />
    </svg>
    <span className={`absolute font-bold ${f} ${cl}`}>{score}%</span>
  </div>;
}
