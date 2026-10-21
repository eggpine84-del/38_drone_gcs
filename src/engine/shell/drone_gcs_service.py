"""드론 관제 셸 서비스 오케스트레이터 (Drone GCS Service Shell).

Pure Core(drone_state_machine)와 Shell 불변 원장(drone_repository)을 조율.
선검증 후적재 파이프라인으로 실패 시 원장 오염 0% 보장.
"""

from dataclasses import dataclass

from src.engine.core.drone_state_machine import (
    DroneStatus,
    TelemetrySnapshot,
    evaluate_state_transition,
)
from src.engine.core.telemetry_record import TelemetryRecord
from src.engine.shell.drone_repository import DroneLedgerRepository


@dataclass(frozen=True)
class IngestPayload:
    """수신된 텔레메트리 입력 페이로드."""

    drone_id: str
    latitude: float
    longitude: float
    altitude: float
    speed: float
    battery: int
    target_status: DroneStatus
    timestamp: str


@dataclass(frozen=True)
class IngestResult:
    """텔레메트리 수신 및 원장 적재 결과 봉투."""

    success: bool
    record: TelemetryRecord | None
    is_failsafe_forced: bool
    reason: str
    violations: tuple[str, ...] = ()


class DroneGCSService:
    """드론 관제 비즈니스 서비스 오케스트레이터."""

    def __init__(self, repository: DroneLedgerRepository) -> None:
        self._repository = repository

    def process_telemetry(self, payload: IngestPayload) -> IngestResult:
        """텔레메트리를 검증하고 4대 공리 충족 시 불변 원장에 적재합니다."""
        # 1. 조기 반환 가드 (빈 drone_id 방어)
        if not payload.drone_id or not payload.drone_id.strip():
            return IngestResult(
                success=False,
                record=None,
                is_failsafe_forced=False,
                reason="INVALID_DRONE_ID",
                violations=("EMPTY_DRONE_ID",),
            )

        # 2. 직전 비행 상태 조회 (Shell I/O)
        latest_record = self._repository.get_latest(payload.drone_id)
        current_status = (
            DroneStatus(latest_record.status) if latest_record else DroneStatus.IDLE
        )

        # 3. Pure Core 검증 및 전이 판정 (외부 I/O 0건)
        snapshot = TelemetrySnapshot(
            battery=payload.battery,
            altitude=payload.altitude,
            latitude=payload.latitude,
            longitude=payload.longitude,
            speed=payload.speed,
        )
        transition = evaluate_state_transition(
            current_status=current_status,
            target_status=payload.target_status,
            telemetry=snapshot,
        )

        # 4. 검증 실패 시: 원장 적재 0건 차단 (원장 오염 방어)
        if not transition.success:
            return IngestResult(
                success=False,
                record=None,
                is_failsafe_forced=False,
                reason=transition.reason,
                violations=transition.violations,
            )

        # 5. 검증 성공 시: 확정된 상태로 TelemetryRecord 생성 후 원장 영구 적재 (Shell I/O)
        record_to_append = TelemetryRecord(
            drone_id=payload.drone_id,
            latitude=payload.latitude,
            longitude=payload.longitude,
            altitude=payload.altitude,
            speed=payload.speed,
            battery=payload.battery,
            status=transition.next_status.value,
            timestamp=payload.timestamp,
        )
        persisted_record = self._repository.append(record_to_append)

        return IngestResult(
            success=True,
            record=persisted_record,
            is_failsafe_forced=transition.is_failsafe_forced,
            reason=transition.reason,
            violations=(),
        )

    def get_latest_telemetry(self, drone_id: str) -> TelemetryRecord | None:
        """특정 드론의 가장 최신 텔레메트리 원장을 조회합니다."""
        return self._repository.get_latest(drone_id)

    def get_flight_history(
        self, drone_id: str, limit: int = 50
    ) -> list[TelemetryRecord]:
        """특정 드론의 비행 이력을 순차 조회합니다."""
        return self._repository.list_by_drone(drone_id, limit=limit)
