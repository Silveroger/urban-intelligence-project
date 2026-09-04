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
