# -*- coding: utf-8 -*-
"""MAVLink 순수 코어 파서 핀-테스트 (Pure Core Pin-Test).

FCIS 헌법 준수: 외부 I/O 0건, Side-Effect 0건, 0.001초 연산 검증.
"""
import pytest
from src.engine.core.drone_state_machine import DroneStatus
from src.engine.core.mavlink_parser_core import (
    convert_mavlink_to_payload,
    map_mavlink_mode_to_status,
)


def test_1_normal_mavlink_coordinate_and_speed_scaling():
    """정상 MAVLink 패킷 정수(1e7, mm, cm/s)가 정확한 실수 단위로 변환되는지 검증."""
    gps_dict = {
        "lat": 375665000,       # 37.5665 도
        "lon": 1269780000,     # 126.9780 도
        "relative_alt": 25000, # 25.0 m
        "vx": 300,             # 3.0 m/s
        "vy": 400,             # 4.0 m/s -> 합성 속도 5.0 m/s
    }
    heartbeat_dict = {
        "base_mode": 128,      # ARMED
        "custom_mode": 4,      # GUIDED
    }
    battery_dict = {
        "battery_remaining": 88,
    }

    payload = convert_mavlink_to_payload(
        drone_id="DRONE-01",
        gps_msg=gps_dict,
        heartbeat_msg=heartbeat_dict,
        battery_msg=battery_dict,
        timestamp="2026-10-19T10:00:00Z",
    )

    assert payload is not None
    assert payload.drone_id == "DRONE-01"
    assert pytest.approx(payload.latitude, rel=1e-5) == 37.5665
    assert pytest.approx(payload.longitude, rel=1e-5) == 126.9780
    assert pytest.approx(payload.altitude, rel=1e-5) == 25.0
    assert pytest.approx(payload.speed, rel=1e-5) == 5.0
    assert payload.battery == 88
    assert payload.target_status == DroneStatus.IN_FLIGHT
    assert payload.timestamp == "2026-10-19T10:00:00Z"


def test_2_table_driven_flight_mode_mapping():
    """MAVLink 플래그에 따른 Table-Driven 상태 매핑 검증."""
    # 1. 시동 꺼짐 (base_mode & 128 == 0) -> IDLE
    status_disarmed = map_mavlink_mode_to_status(base_mode=0, custom_mode=0, altitude=0.0)
    assert status_disarmed == DroneStatus.IDLE

    # 2. 시동 켜짐 + 고도 0 -> ARMED
    status_armed = map_mavlink_mode_to_status(base_mode=128, custom_mode=4, altitude=0.0)
    assert status_armed == DroneStatus.ARMED

    # 3. 시동 켜짐 + 비행 중 (고도 > 0.5) -> IN_FLIGHT
    status_flying = map_mavlink_mode_to_status(base_mode=128, custom_mode=4, altitude=10.0)
    assert status_flying == DroneStatus.IN_FLIGHT

    # 4. RTL 모드 (custom_mode == 6) -> EMERGENCY_RTH
    status_rtl = map_mavlink_mode_to_status(base_mode=128, custom_mode=6, altitude=10.0)
    assert status_rtl == DroneStatus.EMERGENCY_RTH

    # 5. LAND 모드 (custom_mode == 9) -> LANDING
    status_land = map_mavlink_mode_to_status(base_mode=128, custom_mode=9, altitude=2.0)
    assert status_land == DroneStatus.LANDING


def test_3_hidden_outliers_and_guard_clauses():
    """비정형 데이터 및 3대 돌출값 차단 검증."""
    gps_dict = {"lat": 375665000, "lon": 1269780000, "relative_alt": 10000, "vx": 0, "vy": 0}
    heartbeat_dict = {"base_mode": 128, "custom_mode": 4}
    battery_dict = {"battery_remaining": 50}

    # 1. 빈 drone_id 차단 -> None
    res_empty_id = convert_mavlink_to_payload(
        drone_id="   ",
        gps_msg=gps_dict,
        heartbeat_msg=heartbeat_dict,
        battery_msg=battery_dict,
        timestamp="2026-10-19T10:00:00Z",
    )
    assert res_empty_id is None

    # 2. GPS No-Fix (0.0, 0.0 더미 좌표) 침투 차단 -> None
    res_dummy_gps = convert_mavlink_to_payload(
        drone_id="DRONE-01",
        gps_msg={"lat": 0, "lon": 0, "relative_alt": 0, "vx": 0, "vy": 0},
        heartbeat_msg=heartbeat_dict,
        battery_msg=battery_dict,
        timestamp="2026-10-19T10:00:00Z",
    )
    assert res_dummy_gps is None

    # 3. 배터리 음수(-1) 또는 100 초과 비정상값 클램핑
    res_battery_clamp = convert_mavlink_to_payload(
        drone_id="DRONE-01",
        gps_msg=gps_dict,
        heartbeat_msg=heartbeat_dict,
        battery_msg={"battery_remaining": -5},
        timestamp="2026-10-19T10:00:00Z",
    )
    assert res_battery_clamp is not None
    assert res_battery_clamp.battery == 0

    res_battery_clamp_high = convert_mavlink_to_payload(
        drone_id="DRONE-01",
        gps_msg=gps_dict,
        heartbeat_msg=heartbeat_dict,
        battery_msg={"battery_remaining": 150},
        timestamp="2026-10-19T10:00:00Z",
    )
    assert res_battery_clamp_high is not None
    assert res_battery_clamp_high.battery == 100
