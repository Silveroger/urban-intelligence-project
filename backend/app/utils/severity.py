"""
Severity Mapping & Conversion Utility
- Internal numeric representation: 1 (Low), 2 (Moderate), 3 (High), 4 (Critical)
- External API / UI representation: "low", "moderate", "high", "critical"
"""
from typing import Union, Optional

SEVERITY_INT_TO_TEXT = {
    1: "low",
    2: "moderate",
    3: "high",
    4: "critical",
}

SEVERITY_TEXT_TO_INT = {
    "low": 1,
    "minor": 1,
    "moderate": 2,
    "medium": 2,
    "high": 3,
    "severe": 3,
    "critical": 4,
}

SEVERITY_WEIGHTS = {
    1: 2.0,   # Low
    2: 5.0,   # Moderate
    3: 10.0,  # High
    4: 20.0,  # Critical
}


def severity_to_text(val: Optional[Union[int, str]]) -> str:
    """Converts internal integer or text severity to descriptive lowercase text."""
    if val is None:
        return "low"
    if isinstance(val, int):
        return SEVERITY_INT_TO_TEXT.get(val, "low")
    val_str = str(val).strip().lower()
    if val_str.isdigit():
        return SEVERITY_INT_TO_TEXT.get(int(val_str), "low")
    return SEVERITY_INT_TO_TEXT.get(SEVERITY_TEXT_TO_INT.get(val_str, 1), val_str)


def severity_to_int(val: Optional[Union[int, str]]) -> int:
    """Converts descriptive text or raw value to internal numeric severity (1-4)."""
    if val is None:
        return 1
    if isinstance(val, int):
        return max(1, min(4, val))
    val_str = str(val).strip().lower()
    if val_str.isdigit():
        return max(1, min(4, int(val_str)))
    return SEVERITY_TEXT_TO_INT.get(val_str, 1)


def get_severity_weight(val: Optional[Union[int, str]]) -> float:
    """Returns scoring penalty weight for the given severity."""
    severity_int = severity_to_int(val)
    return SEVERITY_WEIGHTS.get(severity_int, 2.0)
