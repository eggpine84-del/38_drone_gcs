# -*- coding: utf-8 -*-
"""시동(ARMED) 후 이륙/상승 시 비행 중(IN_FLIGHT) 직접 전이 허용 핀-테스트.

조종사 스로틀/조그 제어 또는 직접 이륙 시 ARMED -> IN_FLIGHT 상태 전이를 100% 보장.
"""
from src.engine.core.drone_state_machine import (
    DroneStatus,
    TelemetrySnapshot,
    evaluate_state_transition,
)


def test_pin_armed_to_in_flight_transition():
    """ARMED 상태에서 고도 0.5m 초과 시 IN_FLIGHT로 전이 승인되는지 검증."""
    snapshot = TelemetrySnapshot(
        battery=99,
        altitude=1.5,
        latitude=-35.36335,
        longitude=149.16524,
        speed=0.5,
    )

    result = evaluate_state_transition(
        current_status=DroneStatus.ARMED,
        target_status=DroneStatus.IN_FLIGHT,
        telemetry=snapshot,
    )

    assert result.success is True
    assert result.next_status == DroneStatus.IN_FLIGHT
    assert result.is_failsafe_forced is False
    assert result.reason == "TRANSITION_APPROVED"
