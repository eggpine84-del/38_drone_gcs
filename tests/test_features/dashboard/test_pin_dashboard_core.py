# -*- coding: utf-8 -*-
# [파일명]: test_pin_dashboard_core.py
# [목적]: 관제 대시보드 Pure Core 연산 핀-테스트 (외부 I/O 0건, 결정론적 연산 검증)
import pytest
from src.features.dashboard.core.dashboard_core import (
    compute_dashboard_summary,
    format_drone_card_data,
)


def test_pin_empty_telemetry_summary():
    """드론 데이터가 0건일 때 크래시 없이 0대 정상 요약 객체를 반환하는지 검증."""
    result = compute_dashboard_summary([])
    assert result["total_drones"] == 0
    assert result["active_in_flight"] == 0
    assert result["emergency_count"] == 0
    assert result["avg_battery"] == 0
    assert result["has_emergency"] is False
    assert result["drone_cards"] == []


def test_pin_multi_drone_telemetry_summary():
    """다중 드론 텔레메트리 입력 시 집계 및 비상 경보 플래그가 정확히 계산되는지 검증."""
    records = [
        {
            "drone_id": "DRONE-01",
            "status": "IN_FLIGHT",
            "battery": 80,
            "altitude": 50.0,
            "speed": 12.0,
            "latitude": 37.5665,
            "longitude": 126.9780,
            "timestamp": "2026-10-18T14:00:00Z",
        },
        {
            "drone_id": "DRONE-02",
            "status": "EMERGENCY_RTH",
            "battery": 14,
            "altitude": 30.0,
            "speed": 8.0,
            "latitude": 37.5660,
            "longitude": 126.9770,
            "timestamp": "2026-10-18T14:00:01Z",
        },
        {
            "drone_id": "DRONE-03",
            "status": "ARMED",
            "battery": 96,
            "altitude": 0.0,
            "speed": 0.0,
            "latitude": 37.5655,
            "longitude": 126.9760,
            "timestamp": "2026-10-18T14:00:02Z",
        },
    ]

    result = compute_dashboard_summary(records)
    assert result["total_drones"] == 3
    assert result["active_in_flight"] == 1
    assert result["emergency_count"] == 1
    assert result["has_emergency"] is True
    # 평균 배터리: (80 + 14 + 96) / 3 = 63.33 -> 63
    assert result["avg_battery"] == 63
    assert len(result["drone_cards"]) == 3


def test_pin_telemetry_outlier_clamping():
    """배터리 및 고도의 비정상적 음수/초과값이 안전하게 클램핑되는지 검증."""
    raw_data = {
        "drone_id": "DRONE-99",
        "status": "TAKEOFF",
        "battery": -10,  # 음수 돌출값
        "altitude": -5.0,  # 음수 고도
        "speed": -2.0,
        "latitude": 37.5665,
        "longitude": 126.9780,
        "timestamp": "2026-10-18T14:00:00Z",
    }
    card = format_drone_card_data(raw_data)
    assert card["battery"] == 0
    assert card["altitude"] == 0.0
    assert card["speed"] == 0.0

    raw_data_overflow = {
        "drone_id": "DRONE-100",
        "status": "IN_FLIGHT",
        "battery": 150,  # 100 초과값
        "altitude": 100.0,
        "speed": 20.0,
        "latitude": 37.5665,
        "longitude": 126.9780,
        "timestamp": "2026-10-18T14:00:00Z",
    }
    card_overflow = format_drone_card_data(raw_data_overflow)
    assert card_overflow["battery"] == 100


def test_pin_status_styling_mapping():
    """비행 상태에 따른 테마 색상 및 경보 등급 매핑 검증."""
    rth_card = format_drone_card_data({
        "drone_id": "DRONE-ALERT",
        "status": "EMERGENCY_RTH",
        "battery": 10,
        "altitude": 20.0,
        "speed": 5.0,
        "latitude": 37.5665,
        "longitude": 126.9780,
        "timestamp": "2026-10-18T14:00:00Z",
    })
    assert rth_card["is_emergency"] is True
    assert "red" in rth_card["status_color_class"]

    flight_card = format_drone_card_data({
        "drone_id": "DRONE-NORMAL",
        "status": "IN_FLIGHT",
        "battery": 90,
        "altitude": 50.0,
        "speed": 15.0,
        "latitude": 37.5665,
        "longitude": 126.9780,
        "timestamp": "2026-10-18T14:00:00Z",
    })
    assert flight_card["is_emergency"] is False
    assert "cyan" in flight_card["status_color_class"]
