/**
 * DecisionBadge — Visual decision indicator for AI matching
 * Shows 🟢 Accepted / 🟡 Review / 🔴 Rejected with color coding
 */

interface DecisionBadgeProps {
  score: number; // 0-100
  decision: 'accepted' | 'review' | 'rejected';
  showLabel?: boolean;
}

const decisionConfig = {
  accepted: {
    color: 'bg-green-100 text-green-900 border-green-300',
    emoji: '🟢',
    label: 'Accepted',
    message: 'Strong match - ready for next step',
  },
  review: {
    color: 'bg-yellow-100 text-yellow-900 border-yellow-300',
    emoji: '🟡',
    label: 'To Review',
    message: 'Good potential - worth deeper look',
  },
  rejected: {
    color: 'bg-red-100 text-red-900 border-red-300',
    emoji: '🔴',
    label: 'Not Matched',
    message: 'Limited alignment - keep exploring',
  },
};

export default function DecisionBadge({ score, decision, showLabel = true }: DecisionBadgeProps) {
  const config = decisionConfig[decision];

  return (
    <div className={`inline-flex items-center gap-2 px-4 py-2 rounded-full border-2 ${config.color}`}>
      <span className="text-xl">{config.emoji}</span>
      <div>
        <div className="font-bold text-sm">{config.label}</div>
        {showLabel && <div className="text-xs opacity-75">{config.message}</div>}
        <div className="text-xs font-mono">{score.toFixed(1)}%</div>
      </div>
    </div>
  );
}
