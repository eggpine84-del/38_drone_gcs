# -*- coding: utf-8 -*-
# [파일명]: test_pin_drone_gcs_service.py (도메인 비즈니스 Shell 서비스 선행 핀-테스트)
# [원칙] 1. 선검증 후적재 원장 오염 0% 방어 | 2. 15% 배터리 RTH 강제 전환 | 3. Full-Assertion
import pytest
from src.engine.core.drone_state_machine import DroneStatus
from src.engine.shell.drone_gcs_service import DroneGCSService, IngestPayload, IngestResult
from src.engine.shell.drone_repository import InMemoryDroneLedgerRepository


@pytest.fixture
def service():
    """인메모리 격리 원장을 주입받은 드론 관제 서비스 픽스처."""
    repo = InMemoryDroneLedgerRepository()
    return DroneGCSService(repository=repo)


def test_pin_service_initial_idle_to_armed_success(service):
    """최초 인입 드론의 정상 IDLE -> ARMED 전이 및 원장 적재 검증 (Full-Assertion)."""
    payload = IngestPayload(
        drone_id="DRONE-01",
        latitude=37.5665,
        longitude=126.9780,
        altitude=0.0,
        speed=0.0,
        battery=100,
        target_status=DroneStatus.ARMED,
        timestamp="2026-10-18T14:00:00Z",
    )
    result = service.process_telemetry(payload)

    assert result.success is True
    assert result.is_failsafe_forced is False
    assert result.reason == "TRANSITION_APPROVED"
    assert result.record is not None
    assert result.record.drone_id == "DRONE-01"
    assert result.record.status == DroneStatus.ARMED
    assert result.record.id == 1


def test_pin_service_rejects_sensor_anomaly_without_ledger_pollution(service):
    """뇌관 1 방어: 고도 음수값 센서 노이즈 인입 시 원장 적재 0건 및 실패 반환 (Full-Assertion)."""
    payload = IngestPayload(
        drone_id="DRONE-01",
        latitude=37.5665,
        longitude=126.9780,
        altitude=-10.0,  # 불가 고도
        speed=0.0,
        battery=80,
        target_status=DroneStatus.ARMED,
        timestamp="2026-10-18T14:00:00Z",
    )
    result = service.process_telemetry(payload)

    assert result.success is False
    assert result.record is None
    assert result.reason == "INVALID_SENSOR_INVARIANT"
    assert "ALTITUDE_NEGATIVE" in result.violations

    # 원장에 오염 데이터가 전혀 적재되지 않았는지 단언
    assert service.get_latest_telemetry("DRONE-01") is None


def test_pin_service_rejects_teleportation_without_ledger_pollution(service):
    """뇌관 1 방어: IDLE 상태에서 IN_FLIGHT 순간이동 요청 시 원장 적재 0건 및 거절 (Full-Assertion)."""
    payload = IngestPayload(
        drone_id="DRONE-01",
        latitude=37.5665,
        longitude=126.9780,
        altitude=0.0,
        speed=0.0,
        battery=80,
        target_status=DroneStatus.IN_FLIGHT,  # 불법 순간이동
        timestamp="2026-10-18T14:00:00Z",
    )
    result = service.process_telemetry(payload)

    assert result.success is False
    assert result.record is None
    assert result.reason == "TRANSITION_PATH_FORBIDDEN"
    assert service.get_latest_telemetry("DRONE-01") is None


def test_pin_service_forces_emergency_rth_on_low_battery(service):
    """뇌관 2 방어: 배터리 15% 이하 시 요청과 무관하게 EMERGENCY_RTH로 원장 강제 박제 (Full-Assertion)."""
    # 1. 시동
    service.process_telemetry(IngestPayload("DRONE-01", 37.5665, 126.9780, 0.0, 0.0, 90, DroneStatus.ARMED, "2026-10-18T14:00:00Z"))
    # 2. 이륙
    service.process_telemetry(IngestPayload("DRONE-01", 37.5665, 126.9780, 10.0, 5.0, 85, DroneStatus.TAKEOFF, "2026-10-18T14:00:01Z"))
    # 3. 비행 중
    service.process_telemetry(IngestPayload("DRONE-01", 37.5665, 126.9780, 50.0, 15.0, 80, DroneStatus.IN_FLIGHT, "2026-10-18T14:00:02Z"))

    # 4. 배터리 급락 (14%) 상태에서 드론이 계속 IN_FLIGHT 유지 요청
    low_bat_payload = IngestPayload(
        drone_id="DRONE-01",
        latitude=37.5665,
        longitude=126.9780,
        altitude=50.0,
        speed=15.0,
        battery=14,
        target_status=DroneStatus.IN_FLIGHT,
        timestamp="2026-10-18T14:00:03Z",
    )
    result = service.process_telemetry(low_bat_payload)

    assert result.success is True
    assert result.is_failsafe_forced is True
    assert result.reason == "FAILSAFE_LOW_BATTERY_RTH"
    assert result.record is not None
    assert result.record.status == DroneStatus.EMERGENCY_RTH

    # 원장에 최종 기록된 상태도 EMERGENCY_RTH여야 함
    latest = service.get_latest_telemetry("DRONE-01")
    assert latest is not None
    assert latest.status == DroneStatus.EMERGENCY_RTH
