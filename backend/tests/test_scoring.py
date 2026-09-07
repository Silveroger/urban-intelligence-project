from app.services.scoring import calculate_road_health


def test_calculate_road_health_empty():
    score, condition = calculate_road_health([])
    assert score == 100.0
    assert condition == "good"


def test_calculate_road_health_single_low():
    obs = [{"observation_type": "road_defect", "severity": 1, "confidence": 0.90}]
    score, condition = calculate_road_health(obs)
    # 100 - 2.0 = 98.0
    assert score == 98.0
    assert condition == "good"


def test_calculate_road_health_single_critical():
    obs = [{"observation_type": "road_defect", "severity": 4, "confidence": 0.90}]
    score, condition = calculate_road_health(obs)
    # 100 - 20.0 = 80.0
    assert score == 80.0
    assert condition == "good"


def test_calculate_road_health_repeated_defects():
    # 3 potholes of severity 2 (base weight 5)
    # repeated factor = min(3-1, 4) = 2 -> 1 + 0.2*2 = 1.4
    # penalty per pothole = 5 * 1.4 = 7.0
    # total penalty = 3 * 7.0 = 21.0
    obs = [
        {"observation_type": "road_defect", "severity": 2, "confidence": 0.8},
        {"observation_type": "road_defect", "severity": 2, "confidence": 0.8},
        {"observation_type": "road_defect", "severity": 2, "confidence": 0.8},
    ]
    score, condition = calculate_road_health(obs)
    assert score == 79.0
    assert condition == "fair"


def test_calculate_road_health_condition_thresholds():
    # Critical threshold: score < 40.0
    severe_obs = [
        {"observation_type": "road_defect", "severity": 4, "confidence": 0.9},
        {"observation_type": "road_defect", "severity": 4, "confidence": 0.9},
        {"observation_type": "road_defect", "severity": 4, "confidence": 0.9},
        {"observation_type": "road_defect", "severity": 4, "confidence": 0.9},
    ]
    score, condition = calculate_road_health(severe_obs)
    assert score < 40.0
    assert condition == "critical"


def test_calculate_road_health_confidence_weighting():
    # Base penalty for severity 1 is 2.0
    # With confidence 0.50 and weight_by_confidence=True -> penalty = 2.0 * 0.50 = 1.0 -> score = 99.0
    obs = [{"observation_type": "road_defect", "severity": 1, "confidence": 0.50}]
    score, condition = calculate_road_health(obs, weight_by_confidence=True)
    assert score == 99.0
    assert condition == "good"


def test_calculate_road_health_clean_pass_recovery():
    # Defect with penalty 20 -> score 80
    # Followed by 2 clean passes (+5 each = +10) -> score 90
    obs = [
        {"observation_type": "road_defect", "severity": 4, "confidence": 1.0},
        {"observation_type": "clean_pass"},
        {"observation_type": "clean_pass"},
    ]
    score, condition = calculate_road_health(obs)
    assert score == 90.0
    assert condition == "good"
