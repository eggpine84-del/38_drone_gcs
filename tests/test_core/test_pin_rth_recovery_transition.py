# -*- coding: utf-8 -*-
"""비상 귀환(EMERGENCY_RTH) 후 지상 대기(IDLE) 정상 복귀 핀-테스트.

기체가 비상 착륙 또는 현장 안전 점검/재부팅 후 지상 대기(IDLE) 상태로 정상 복귀하는 생명주기를 100% 보장.
"""
import pytest
from src.engine.core.drone_state_machine import (
    DroneStatus,
    TelemetrySnapshot,
    evaluate_state_transition,
)


def test_pin_emergency_rth_to_idle_recovery():
    """EMERGENCY_RTH 상태에서 지상 대기(IDLE, 배터리 정상 회복)로 전이 허용을 검증."""
    snapshot = TelemetrySnapshot(
        battery=100,
        altitude=0.0,
        latitude=37.5665,
        longitude=126.9780,
        speed=0.0,
    )

    result = evaluate_state_transition(
        current_status=DroneStatus.EMERGENCY_RTH,
        target_status=DroneStatus.IDLE,
        telemetry=snapshot,
    )

    assert result.success is True
    assert result.next_status == DroneStatus.IDLE
    assert result.is_failsafe_forced is False
    assert result.reason == "TRANSITION_APPROVED"
