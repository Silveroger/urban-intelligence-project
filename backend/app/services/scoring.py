"""
Road Health Scoring Service
Implements deterministic scoring formula based on detected road observations and defects.
"""
from typing import List, Dict, Any, Tuple
from app.utils.severity import severity_to_int, SEVERITY_WEIGHTS


def calculate_road_health(
    observations: List[Dict[str, Any]],
    weight_by_confidence: bool = False,
    clean_pass_recovery: float = 5.0,
) -> Tuple[float, str]:
    """
    Calculates deterministic health score (0-100) and condition category.

    Formula:
      severity_weight = {1: 2, 2: 5, 3: 10, 4: 20}
      For each confirmed observation (confidence >= 0.50):
        confidence_factor = confidence if weight_by_confidence else 1.0
        penalty += severity_weight[severity] * (1.0 + 0.2 * min(count_same_type - 1, 4)) * confidence_factor
      recovery = clean_pass_count * clean_pass_recovery
      health_score = max(0.0, min(100.0, round(100.0 - total_penalty + recovery, 2)))

    Condition mapping:
      >= 80.0 -> "good"
      >= 60.0 -> "fair"
      >= 40.0 -> "poor"
      < 40.0  -> "critical"
    """
    if not observations:
        return 100.0, "good"

    # Separate clean passes from defects
    defect_obs = []
    clean_pass_count = 0
    for obs in observations:
        otype = str(obs.get("observation_type") or obs.get("event_type") or obs.get("class_name") or "road_defect").lower()
        if otype in ("clean_pass", "clear_pass", "clean", "pass"):
            clean_pass_count += 1
        else:
            defect_obs.append(obs)

    # Count occurrences by observation type for frequency multiplier
    type_counts: Dict[str, int] = {}
    for obs in defect_obs:
        otype = str(obs.get("observation_type") or obs.get("event_type") or "road_defect").lower()
        type_counts[otype] = type_counts.get(otype, 0) + 1

    total_penalty = 0.0
    for obs in defect_obs:
        sev_int = severity_to_int(obs.get("severity"))
        base_weight = SEVERITY_WEIGHTS.get(sev_int, 2.0)

        otype = str(obs.get("observation_type") or obs.get("event_type") or "road_defect").lower()
        same_type_count = type_counts.get(otype, 1)

        # Frequency multiplier: repeated defects on same segment escalate impact up to +80%
        repeat_factor = min(max(0, same_type_count - 1), 4)
        frequency_multiplier = 1.0 + (0.2 * repeat_factor)

        conf = float(obs.get("confidence") or 1.0) if weight_by_confidence else 1.0
        total_penalty += base_weight * frequency_multiplier * conf

    recovery_bonus = clean_pass_count * clean_pass_recovery
    final_score = max(0.0, min(100.0, round(100.0 - total_penalty + recovery_bonus, 2)))

    if final_score >= 80.0:
        condition = "good"
    elif final_score >= 60.0:
        condition = "fair"
    elif final_score >= 40.0:
        condition = "poor"
    else:
        condition = "critical"

    return final_score, condition
