# -*- coding: utf-8 -*-
"""드론 관제 순수 코어 상태머신 (DroneGCS Core).

CONSTITUTION.md 4대 공리 및 3대 금기를 기계적으로 강제하는 순수 결정론적 상태 전이 엔진.
외부 I/O 0건, 부작용(Side-Effect) 0건, 0.001초 연산 보장.
"""
from dataclasses import dataclass
from enum import Enum
from typing import Final, FrozenSet, Tuple


class DroneStatus(str, Enum):
    """드론 7대 공인 비행 상태."""
    IDLE = "IDLE"
    ARMED = "ARMED"
    TAKEOFF = "TAKEOFF"
    IN_FLIGHT = "IN_FLIGHT"
    LANDING = "LANDING"
    TERMINATED = "TERMINATED"
    EMERGENCY_RTH = "EMERGENCY_RTH"


@dataclass(frozen=True)
class TelemetrySnapshot:
    """순수 텔레메트리 스냅샷 (Pure Input)."""
    battery: int
    altitude: float
    latitude: float
    longitude: float
    speed: float


@dataclass(frozen=True)
class TransitionResult:
    """상태 전이 판정 결과 봉투 (Pure Output)."""
    success: bool
    next_status: DroneStatus
    is_failsafe_forced: bool
    reason: str
    violations: Tuple[str, ...] = ()


# Table-Driven Dispatch: 상태별 허용된 다음 상태 매핑 테이블 (공리 2: 단방향 상태 전이)
ALLOWED_TRANSITIONS: Final[dict[DroneStatus, FrozenSet[DroneStatus]]] = {
    DroneStatus.IDLE: frozenset({DroneStatus.ARMED}),
    DroneStatus.ARMED: frozenset({DroneStatus.TAKEOFF, DroneStatus.IDLE}),
    DroneStatus.TAKEOFF: frozenset({DroneStatus.IN_FLIGHT, DroneStatus.LANDING, DroneStatus.EMERGENCY_RTH}),
    DroneStatus.IN_FLIGHT: frozenset({DroneStatus.LANDING, DroneStatus.EMERGENCY_RTH}),
    DroneStatus.LANDING: frozenset({DroneStatus.IDLE, DroneStatus.TERMINATED, DroneStatus.EMERGENCY_RTH}),
    DroneStatus.TERMINATED: frozenset(),  # 종결 상태: 추가 전이 영구 불허 (공리 2 및 금기 3)
    DroneStatus.EMERGENCY_RTH: frozenset({DroneStatus.LANDING, DroneStatus.TERMINATED}),
}

MIN_BATTERY: Final[int] = 0
MAX_BATTERY: Final[int] = 100
LOW_BATTERY_THRESHOLD: Final[int] = 15
MIN_ALTITUDE: Final[float] = 0.0
MIN_LATITUDE: Final[float] = -90.0
MAX_LATITUDE: Final[float] = 90.0
MIN_LONGITUDE: Final[float] = -180.0
MAX_LONGITUDE: Final[float] = 180.0
MIN_SPEED: Final[float] = 0.0


def validate_telemetry_invariants(telemetry: TelemetrySnapshot) -> Tuple[str, ...]:
    """공리 1(신호 불변성)을 순수 검증하고 위반 사유 튜플을 반환합니다."""
    violations = []
    if telemetry.battery < MIN_BATTERY or telemetry.battery > MAX_BATTERY:
        violations.append("BATTERY_OUT_OF_RANGE")
    if telemetry.altitude < MIN_ALTITUDE:
        violations.append("ALTITUDE_NEGATIVE")
    if telemetry.latitude < MIN_LATITUDE or telemetry.latitude > MAX_LATITUDE:
        violations.append("GPS_LATITUDE_OUT_OF_RANGE")
    if telemetry.longitude < MIN_LONGITUDE or telemetry.longitude > MAX_LONGITUDE:
        violations.append("GPS_LONGITUDE_OUT_OF_RANGE")
    if telemetry.speed < MIN_SPEED:
        violations.append("SPEED_NEGATIVE")
    return tuple(violations)


def evaluate_state_transition(
    current_status: DroneStatus,
    target_status: DroneStatus,
    telemetry: TelemetrySnapshot,
) -> TransitionResult:
    """드론 상태 전이를 4대 공리에 따라 순수 결정론적으로 평가합니다.

    Args:
        current_status: 현재 비행 상태
        target_status: 전환 희망 목표 상태
        telemetry: 실시간 텔레메트리 스냅샷 (외부 I/O 없이 주입)

    Returns:
        TransitionResult: 상태 전이 결과 객체
    """
    # 1. 공리 1(신호 불변성) 검증: 센서 이상값 차단
    violations = validate_telemetry_invariants(telemetry)
    if violations:
        return TransitionResult(
            success=False,
            next_status=current_status,
            is_failsafe_forced=False,
            reason="INVALID_SENSOR_INVARIANT",
            violations=violations,
        )

    # 2. 공리 2 & 금기 3(단방향 종결): 종결(TERMINATED) 상태는 어떤 상태로도 전이 불가
    if current_status == DroneStatus.TERMINATED:
        return TransitionResult(
            success=False,
            next_status=DroneStatus.TERMINATED,
            is_failsafe_forced=False,
            reason="TERMINAL_STATE_CANNOT_TRANSITION",
            violations=(),
        )

    # 3. 공리 3(위험 격리 및 강제 안전권한): 배터리 15% 이하 시 즉시 EMERGENCY_RTH 강제 전환
    if telemetry.battery <= LOW_BATTERY_THRESHOLD:
        return TransitionResult(
            success=True,
            next_status=DroneStatus.EMERGENCY_RTH,
            is_failsafe_forced=True,
            reason="FAILSAFE_LOW_BATTERY_RTH",
            violations=(),
        )

    # 4. 동일 상태 유지 허용 (비행 지속 등)
    if current_status == target_status:
        return TransitionResult(
            success=True,
            next_status=current_status,
            is_failsafe_forced=False,
            reason="TRANSITION_MAINTAINED",
            violations=(),
        )

    # 5. Table-Driven Dispatch: 허용된 단방향 전이 경로 검증
    allowed_next_states = ALLOWED_TRANSITIONS.get(current_status, frozenset())
    if target_status not in allowed_next_states:
        return TransitionResult(
            success=False,
            next_status=current_status,
            is_failsafe_forced=False,
            reason="TRANSITION_PATH_FORBIDDEN",
            violations=(),
        )

    # 6. 정상 전이 승인
    return TransitionResult(
        success=True,
        next_status=target_status,
        is_failsafe_forced=False,
        reason="TRANSITION_APPROVED",
        violations=(),
    )
