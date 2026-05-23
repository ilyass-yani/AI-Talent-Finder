"""Phase 3: Bias Detection System - Monitor fairness in recruiter decisions."""

from dataclasses import dataclass
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import re


@dataclass
class BiasAlert:
    """Alert for potential bias detected."""
    alert_type: str  # "acceptance_rate_disparity", "score_gap", "pattern_anomaly"
    severity: str  # "low" | "medium" | "high"
    message: str
    affected_group: str  # e.g., "junior_developers", "candidates_from_east_africa"
    detected_at: datetime
    recommendation: str


class BiasDetector:
    """
    Monitor hiring patterns for potential bias:
    - Acceptance rate disparities by inferred demographics
    - Score distribution anomalies
    - Pattern-based red flags
    """

    def __init__(self, db=None):
        """Initialize detector."""
        self.db = db
        self.alerts: List[BiasAlert] = []

    def analyze_recruiter_decisions(
        self,
        feedback_records: List[Dict],
        min_samples: int = 30,
    ) -> Dict:
        """
        Analyze recruiter decisions for bias indicators.
        
        Args:
            feedback_records: List of recruiter feedback dictionaries
            min_samples: Minimum samples per group for analysis
        
        Returns:
            Report with detected biases and recommendations
        """
        if not feedback_records or len(feedback_records) < min_samples:
            return {"status": "insufficient_data", "sample_count": len(feedback_records)}

        report = {
            "analysis_date": datetime.utcnow().isoformat(),
            "total_records": len(feedback_records),
            "alerts": [],
            "disparities": {},
            "recommendations": [],
        }

        # Check acceptance rate disparities
        disparities = self._check_acceptance_disparities(feedback_records)
        if disparities:
            report["disparities"] = disparities
            report["alerts"].extend([d["alert"] for d in disparities.values()])

        # Check score distribution anomalies
        score_check = self._check_score_anomalies(feedback_records)
        if score_check:
            report["alerts"].extend(score_check)

        # Check for pattern anomalies
        patterns = self._check_pattern_anomalies(feedback_records)
        if patterns:
            report["alerts"].extend(patterns)

        # Generate recommendations
        if report["alerts"]:
            report["recommendations"] = self._generate_recommendations(report["alerts"])

        return report

    def _check_acceptance_disparities(self, records: List[Dict]) -> Dict:
        """Check for acceptance rate disparities (the main bias concern)."""
        disparities = {}

        # Group by inferred characteristics from candidate names/emails
        groups = self._group_by_demographics(records)

        if len(groups) < 2:
            return {}

        # Calculate acceptance rates per group
        rates = {}
        for group_name, candidates in groups.items():
            if len(candidates) < 10:  # Skip groups with too few samples
                continue

            accepted = sum(1 for c in candidates if c.get("recruiter_decision") == "accepted")
            rate = accepted / len(candidates)
            rates[group_name] = {
                "rate": rate,
                "count": len(candidates),
                "accepted": accepted,
            }

        # Find disparities (highest and lowest acceptance rates)
        if len(rates) >= 2:
            sorted_rates = sorted(rates.items(), key=lambda x: x[1]["rate"])
            lowest = sorted_rates[0]
            highest = sorted_rates[-1]

            disparity_ratio = (
                highest[1]["rate"] / lowest[1]["rate"]
                if lowest[1]["rate"] > 0
                else float("inf")
            )

            # Flag if disparity > 1.25 (25% difference)
            if disparity_ratio > 1.25:
                alert_msg = (
                    f"Acceptance rate disparity detected: {highest[0]} "
                    f"{highest[1]['rate']:.1%} vs {lowest[0]} {lowest[1]['rate']:.1%}"
                )
                disparities[f"{lowest[0]}_vs_{highest[0]}"] = {
                    "alert": BiasAlert(
                        alert_type="acceptance_rate_disparity",
                        severity="high" if disparity_ratio > 1.5 else "medium",
                        message=alert_msg,
                        affected_group=lowest[0],
                        detected_at=datetime.utcnow(),
                        recommendation=(
                            f"Review scoring/decisions for {lowest[0]}. "
                            f"Conduct blind review process."
                        ),
                    ),
                    "disparity_ratio": disparity_ratio,
                    "rates": rates,
                }

        return disparities

    def _check_score_anomalies(self, records: List[Dict]) -> List[BiasAlert]:
        """Check if score distributions are anomalous."""
        alerts = []

        # Check if same scores are given despite different candidate profiles
        score_consistency = {}
        for record in records:
            score = round(record.get("model_predicted_score", 0))
            if score not in score_consistency:
                score_consistency[score] = []
            score_consistency[score].append(record)

        # Find score buckets with >80% same decision when scores vary
        for score, recs in score_consistency.items():
            if len(recs) < 5:
                continue

            decisions = [r.get("recruiter_decision") for r in recs]
            accepted_ratio = sum(1 for d in decisions if d == "accepted") / len(decisions)

            if accepted_ratio > 0.85 or accepted_ratio < 0.15:
                alerts.append(
                    BiasAlert(
                        alert_type="score_gap",
                        severity="low",
                        message=(
                            f"Unusual decision ratio at score {score}: "
                            f"{accepted_ratio:.0%} acceptance"
                        ),
                        affected_group=f"candidates_at_score_{score}",
                        detected_at=datetime.utcnow(),
                        recommendation="Review scoring function calibration.",
                    )
                )

        return alerts

    def _check_pattern_anomalies(self, records: List[Dict]) -> List[BiasAlert]:
        """Detect suspicious patterns in decisions."""
        alerts = []

        # Pattern 1: Certain recruiters consistently reject certain demographics
        recruiter_patterns = self._analyze_recruiter_patterns(records)
        for recruiter_id, pattern in recruiter_patterns.items():
            if pattern.get("has_bias_flag"):
                alerts.append(
                    BiasAlert(
                        alert_type="pattern_anomaly",
                        severity="medium",
                        message=f"Recruiter {recruiter_id} shows unusual decision pattern",
                        affected_group=f"recruiter_{recruiter_id}",
                        detected_at=datetime.utcnow(),
                        recommendation=(
                            "Audit this recruiter's decisions; "
                            "consider blind review or structured interviews."
                        ),
                    )
                )

        return alerts

    def _group_by_demographics(self, records: List[Dict]) -> Dict[str, List]:
        """Infer demographics from candidate names/emails for bias analysis."""
        groups = {
            "senior": [],
            "junior": [],
            "east_africa": [],
            "west_africa": [],
            "south_asia": [],
            "anglo": [],
        }

        for record in records:
            candidate_name = record.get("candidate_name", "").lower()
            email = record.get("email", "").lower()

            # Infer experience level (heuristic: title/name mentions)
            if any(x in candidate_name for x in ["senior", "lead", "principal"]):
                groups["senior"].append(record)
            else:
                groups["junior"].append(record)

            # Infer geographic/cultural background (name-based, not 100% accurate)
            if self._is_east_african_name(candidate_name):
                groups["east_africa"].append(record)
            elif self._is_west_african_name(candidate_name):
                groups["west_africa"].append(record)
            elif self._is_south_asian_name(candidate_name):
                groups["south_asia"].append(record)
            else:
                groups["anglo"].append(record)

        # Keep only groups with data
        return {k: v for k, v in groups.items() if v}

    def _is_east_african_name(self, name: str) -> bool:
        """Heuristic: detect East African names."""
        patterns = ["njeri", "kipkemboi", "mutua", "koech", "kinyua", "muyeni"]
        return any(p in name for p in patterns)

    def _is_west_african_name(self, name: str) -> bool:
        """Heuristic: detect West African names."""
        patterns = ["okonkwo", "adeyemi", "otchere", "mensah", "diallo", "faye"]
        return any(p in name for p in patterns)

    def _is_south_asian_name(self, name: str) -> bool:
        """Heuristic: detect South Asian names."""
        patterns = ["sharma", "patel", "singh", "gupta", "banerjee", "krishnan"]
        return any(p in name for p in patterns)

    def _analyze_recruiter_patterns(self, records: List[Dict]) -> Dict:
        """Analyze each recruiter's decision patterns."""
        patterns = {}

        for record in records:
            recruiter_id = record.get("recruiter_id", "unknown")
            if recruiter_id not in patterns:
                patterns[recruiter_id] = {
                    "total_decisions": 0,
                    "acceptance_rate": 0.0,
                    "has_bias_flag": False,
                }

            patterns[recruiter_id]["total_decisions"] += 1
            if record.get("recruiter_decision") == "accepted":
                patterns[recruiter_id]["acceptance_rate"] += 1

        # Normalize rates and flag outliers
        for recruiter_id, data in patterns.items():
            if data["total_decisions"] >= 5:
                rate = data["acceptance_rate"] / data["total_decisions"]
                # Flag if acceptance rate < 10% or > 90% (unusually extreme)
                if rate < 0.1 or rate > 0.9:
                    data["has_bias_flag"] = True
                data["acceptance_rate"] = rate

        return patterns

    def _generate_recommendations(self, alerts: List[BiasAlert]) -> List[str]:
        """Generate actionable recommendations based on detected biases."""
        recommendations = [
            "✓ Implement blind resume review (remove names/photos)",
            "✓ Use structured interviews with standardized questions",
            "✓ Train recruiters on unconscious bias",
            "✓ Regular bias audits (monthly minimum)",
            "✓ Document decision rationale for all hires",
        ]

        # Add severity-based recommendations
        high_severity = [a for a in alerts if a.severity == "high"]
        if high_severity:
            recommendations.insert(
                0, "⚠️ HIGH PRIORITY: Halt hiring review for affected groups"
            )

        return recommendations

    def get_alerts_summary(self) -> Dict:
        """Get summary of all detected alerts."""
        if not self.alerts:
            return {"status": "no_alerts", "bias_risk": "low"}

        severity_counts = {}
        for alert in self.alerts:
            severity_counts[alert.severity] = severity_counts.get(alert.severity, 0) + 1

        risk_level = "high" if severity_counts.get("high", 0) > 0 else (
            "medium" if severity_counts.get("medium", 0) > 0 else "low"
        )

        return {
            "status": "alerts_detected",
            "bias_risk": risk_level,
            "alert_counts": severity_counts,
            "alerts": [
                {
                    "type": a.alert_type,
                    "severity": a.severity,
                    "message": a.message,
                    "group": a.affected_group,
                }
                for a in self.alerts[:10]
            ],
        }
