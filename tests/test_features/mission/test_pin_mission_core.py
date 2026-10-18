# -*- coding: utf-8 -*-
# [파일명]: test_pin_mission_core.py
# [목적]: 비행 명령 유효성 및 웨이포인트 진행률 순수 연산 코어 선행 핀-테스트 (외부 I/O 0건)
import pytest
from src.features.mission.core.mission_core import (
    evaluate_command,
    calculate_waypoint_progress,
    validate_waypoints,
    CommandResult,
    ProgressResult,
)


def test_pin_command_precondition_strict_transitions():
    """금기 1항: 선행 상태 검증 없는 임의 비행 명령 하달 차단 검증 (Full-Assertion)."""
    # 1. IDLE(시동 꺼짐) 드론에 즉시 TAKEOFF 명령 -> 거부 (금기 1조 위반 차단)
    fail_takeoff = evaluate_command(current_status="IDLE", command="TAKEOFF", battery=90)
    assert fail_takeoff.is_allowed is False
    assert fail_takeoff.next_status is None
    assert "시동(ARMED)" in fail_takeoff.reason

    # 2. IDLE 상태에서 정상 시동(ARM) 명령 -> 허용
    arm_res = evaluate_command(current_status="IDLE", command="ARM", battery=90)
    assert arm_res.is_allowed is True
    assert arm_res.next_status == "ARMED"

    # 3. ARMED 상태에서 정상 이륙(TAKEOFF) 명령 -> 허용
    takeoff_res = evaluate_command(current_status="ARMED", command="TAKEOFF", battery=85)
    assert takeoff_res.is_allowed is True
    assert takeoff_res.next_status == "TAKEOFF"

    # 4. 저배터리(14%) 상태에서 이륙 시도 -> 거부 (공리 3항 방어)
    low_bat_res = evaluate_command(current_status="ARMED", command="TAKEOFF", battery=14)
    assert low_bat_res.is_allowed is False
    assert "배터리" in low_bat_res.reason

    # 5. 비행 중(IN_FLIGHT)에서 정상 착륙(LAND) 명령 -> 허용
    land_res = evaluate_command(current_status="IN_FLIGHT", command="LAND", battery=50)
    assert land_res.is_allowed is True
    assert land_res.next_status == "LANDING"

    # 6. 비행 중(IN_FLIGHT)에서 비상 귀환(RTH) 명령 -> 허용
    rth_res = evaluate_command(current_status="IN_FLIGHT", command="RTH", battery=40)
    assert rth_res.is_allowed is True
    assert rth_res.next_status == "EMERGENCY_RTH"


def test_pin_waypoint_progress_advancement():
    """웨이포인트 순차 도달(반경 5m 이내) 및 진행률(%) 계산 순수 함수 검증."""
    waypoints = [
        {"latitude": 37.5665, "longitude": 126.9780, "altitude": 30.0},
        {"latitude": 37.5675, "longitude": 126.9780, "altitude": 40.0},
        {"latitude": 37.5685, "longitude": 126.9780, "altitude": 50.0},
    ]

    # 1. 1번 목표점(인덱스 0) 도달 전 (거리 약 50m) -> 인덱스 0 유지, 진행률 0%
    prog_1 = calculate_waypoint_progress(
        current_lat=37.5660,
        current_lon=126.9780,
        current_alt=25.0,
        waypoints=waypoints,
        current_index=0,
        arrival_threshold_m=5.0,
    )
    assert prog_1.current_index == 0
    assert prog_1.progress_pct == 0
    assert prog_1.is_completed is False

    # 2. 1번 목표점 바로 도착 (거리 1m 이내) -> 다음 인덱스 1로 전진, 진행률 33%
    prog_2 = calculate_waypoint_progress(
        current_lat=37.5665,
        current_lon=126.9780,
        current_alt=30.0,
        waypoints=waypoints,
        current_index=0,
        arrival_threshold_m=5.0,
    )
    assert prog_2.current_index == 1
    assert prog_2.progress_pct == 33
    assert prog_2.is_completed is False

    # 3. 마지막 목표점(인덱스 2) 도착 -> 완료(is_completed=True), 진행률 100%
    prog_3 = calculate_waypoint_progress(
        current_lat=37.5685,
        current_lon=126.9780,
        current_alt=50.0,
        waypoints=waypoints,
        current_index=2,
        arrival_threshold_m=5.0,
    )
    assert prog_3.current_index == 3
    assert prog_3.progress_pct == 100
    assert prog_3.is_completed is True


def test_pin_validate_waypoints_boundary_defense():
    """웨이포인트 음수 고도(지하 충돌) 및 빈 목록 유효성 가드 검증."""
    # 빈 리스트 -> 거부
    assert validate_waypoints([]) is False

    # 고도 음수(-10.0m) 포함 -> 지하 충돌 위험으로 거부
    bad_wp = [{"latitude": 37.5665, "longitude": 126.9780, "altitude": -10.0}]
    assert validate_waypoints(bad_wp) is False

    # 정상 웨이포인트 -> 통과
    good_wp = [{"latitude": 37.5665, "longitude": 126.9780, "altitude": 30.0}]
    assert validate_waypoints(good_wp) is True
