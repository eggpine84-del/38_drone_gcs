# -*- coding: utf-8 -*-
# [파일명]: test_pin_drone_state_machine.py (드론 관제 순수 코어 상태머신 선행 핀-테스트)
# [원칙] Full-Assertion 객체 전체 대조 & CONSTITUTION 4대 공리 100% 검증
import pytest
from src.engine.core.drone_state_machine import (
    DroneStatus,
    TransitionResult,
    TelemetrySnapshot,
    evaluate_state_transition,
)


def test_pin_valid_sequential_transition():
    """정상 시퀀스: IDLE -> ARMED 단방향 상태 전이 성공 검증 (Full-Assertion)."""
    snapshot = TelemetrySnapshot(
        battery=90,
        altitude=0.0,
        latitude=37.5665,
        longitude=126.9780,
        speed=0.0,
    )
    result = evaluate_state_transition(
        current_status=DroneStatus.IDLE,
        target_status=DroneStatus.ARMED,
        telemetry=snapshot,
    )
    expected = TransitionResult(
        success=True,
        next_status=DroneStatus.ARMED,
        is_failsafe_forced=False,
        reason="TRANSITION_APPROVED",
        violations=(),
    )
    assert result == expected


def test_pin_telemetry_invariants_battery_out_of_range():
    """공리 1(신호 불변성): 배터리 음수값 유입 시 즉시 거절 및 위반 반환 (Full-Assertion)."""
    snapshot = TelemetrySnapshot(
        battery=-5,
        altitude=10.0,
        latitude=37.5665,
        longitude=126.9780,
        speed=5.0,
    )
    result = evaluate_state_transition(
        current_status=DroneStatus.ARMED,
        target_status=DroneStatus.TAKEOFF,
        telemetry=snapshot,
    )
    expected = TransitionResult(
        success=False,
        next_status=DroneStatus.ARMED,
        is_failsafe_forced=False,
        reason="INVALID_SENSOR_INVARIANT",
        violations=("BATTERY_OUT_OF_RANGE",),
    )
    assert result == expected


def test_pin_telemetry_invariants_negative_altitude():
    """공리 1(신호 불변성): 고도 음수값 유입 시 즉시 거절 (Full-Assertion)."""
    snapshot = TelemetrySnapshot(
        battery=80,
        altitude=-12.5,
        latitude=37.5665,
        longitude=126.9780,
        speed=5.0,
    )
    result = evaluate_state_transition(
        current_status=DroneStatus.IN_FLIGHT,
        target_status=DroneStatus.LANDING,
        telemetry=snapshot,
    )
    expected = TransitionResult(
        success=False,
        next_status=DroneStatus.IN_FLIGHT,
        is_failsafe_forced=False,
        reason="INVALID_SENSOR_INVARIANT",
        violations=("ALTITUDE_NEGATIVE",),
    )
    assert result == expected


def test_pin_telemetry_invariants_gps_out_of_range():
    """공리 1(신호 불변성): 지구상 실존 좌표계 이탈 시 즉시 거절 (Full-Assertion)."""
    snapshot = TelemetrySnapshot(
        battery=80,
        altitude=50.0,
        latitude=95.1234,  # 허용 범위 -90 ~ +90 초과
        longitude=126.9780,
        speed=5.0,
    )
    result = evaluate_state_transition(
        current_status=DroneStatus.IN_FLIGHT,
        target_status=DroneStatus.LANDING,
        telemetry=snapshot,
    )
    expected = TransitionResult(
        success=False,
        next_status=DroneStatus.IN_FLIGHT,
        is_failsafe_forced=False,
        reason="INVALID_SENSOR_INVARIANT",
        violations=("GPS_LATITUDE_OUT_OF_RANGE",),
    )
    assert result == expected


def test_pin_failsafe_preemption_on_low_battery():
    """공리 3(위험 격리 및 강제 안전권한): 배터리 15% 이하 시 목표 상태와 무관하게 EMERGENCY_RTH 강제 전환 (Full-Assertion)."""
    snapshot = TelemetrySnapshot(
        battery=14,  # 15% 이하 임계치
        altitude=60.0,
        latitude=37.5665,
        longitude=126.9780,
        speed=8.0,
    )
    result = evaluate_state_transition(
        current_status=DroneStatus.IN_FLIGHT,
        target_status=DroneStatus.IN_FLIGHT,  # 드론은 비행 유지를 원함
        telemetry=snapshot,
    )
    expected = TransitionResult(
        success=True,
        next_status=DroneStatus.EMERGENCY_RTH,
        is_failsafe_forced=True,
        reason="FAILSAFE_LOW_BATTERY_RTH",
        violations=(),
    )
    assert result == expected


def test_pin_forbid_teleportation_idle_to_in_flight():
    """공리 2 & 금기 1: 시동 없는 대기 상태 드론의 비행 순간이동 차단 (Full-Assertion)."""
    snapshot = TelemetrySnapshot(
        battery=90,
        altitude=0.0,
        latitude=37.5665,
        longitude=126.9780,
        speed=0.0,
    )
    result = evaluate_state_transition(
        current_status=DroneStatus.IDLE,
        target_status=DroneStatus.IN_FLIGHT,  # 순간이동 시도
        telemetry=snapshot,
    )
    expected = TransitionResult(
        success=False,
        next_status=DroneStatus.IDLE,
        is_failsafe_forced=False,
        reason="TRANSITION_PATH_FORBIDDEN",
        violations=(),
    )
    assert result == expected


def test_pin_forbid_terminated_revival():
    """공리 2 & 금기 3: 종결(TERMINATED) 상태 드론의 부활 및 임의 전이 영구 차단 (Full-Assertion)."""
    snapshot = TelemetrySnapshot(
        battery=90,
        altitude=0.0,
        latitude=37.5665,
        longitude=126.9780,
        speed=0.0,
    )
    result = evaluate_state_transition(
        current_status=DroneStatus.TERMINATED,
        target_status=DroneStatus.ARMED,  # 종료된 드론 재시동 시도
        telemetry=snapshot,
    )
    expected = TransitionResult(
        success=False,
        next_status=DroneStatus.TERMINATED,
        is_failsafe_forced=False,
        reason="TERMINAL_STATE_CANNOT_TRANSITION",
        violations=(),
    )
    assert result == expected


def test_pin_pure_core_determinism():
    """G2 규격: 동일 입력 2회 호출 결과 100% 동일성(결정론적 순수성) 검증."""
    snapshot = TelemetrySnapshot(
        battery=75,
        altitude=25.0,
        latitude=37.5665,
        longitude=126.9780,
        speed=10.0,
    )
    res1 = evaluate_state_transition(DroneStatus.TAKEOFF, DroneStatus.IN_FLIGHT, snapshot)
    res2 = evaluate_state_transition(DroneStatus.TAKEOFF, DroneStatus.IN_FLIGHT, snapshot)
    assert res1 == res2
    assert res1.success is True
    assert res1.next_status == DroneStatus.IN_FLIGHT
