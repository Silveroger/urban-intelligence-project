from app.utils.severity import (
    severity_to_text,
    severity_to_int,
    get_severity_weight,
    SEVERITY_WEIGHTS,
)


def test_severity_to_text():
    assert severity_to_text(1) == "low"
    assert severity_to_text(2) == "moderate"
    assert severity_to_text(3) == "high"
    assert severity_to_text(4) == "critical"

    # String input
    assert severity_to_text("1") == "low"
    assert severity_to_text("4") == "critical"
    assert severity_to_text("high") == "high"
    assert severity_to_text("minor") == "low"
    assert severity_to_text("severe") == "high"
    assert severity_to_text(None) == "low"


def test_severity_to_int():
    assert severity_to_int("low") == 1
    assert severity_to_int("moderate") == 2
    assert severity_to_int("high") == 3
    assert severity_to_int("critical") == 4
    assert severity_to_int("minor") == 1
    assert severity_to_int("severe") == 3

    # Numeric input
    assert severity_to_int(1) == 1
    assert severity_to_int(4) == 4
    assert severity_to_int(99) == 4  # Clamped to 4
    assert severity_to_int(-5) == 1  # Clamped to 1
    assert severity_to_int(None) == 1


def test_severity_weights():
    assert get_severity_weight(1) == 2.0
    assert get_severity_weight(2) == 5.0
    assert get_severity_weight(3) == 10.0
    assert get_severity_weight(4) == 20.0
    assert get_severity_weight("high") == 10.0
    assert get_severity_weight("critical") == 20.0
