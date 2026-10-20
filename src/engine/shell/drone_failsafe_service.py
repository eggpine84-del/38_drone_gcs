# -*- coding: utf-8 -*-
"""드론 페일세이프 셸 서비스 (Drone Failsafe Service Shell).

하트비트 수신 추적 및 3초 이상 통신 두절 시 EMERGENCY_RTH 강제 전환 및 멱등 원장 보존.
"""
from dataclasses import dataclass
from typing import Dict, Optional

from src.engine.core.drone_state_machine import DroneStatus
from src.engine.core.failsafe_evaluator import evaluate_heartbeat_timeout
from src.engine.core.telemetry_record import TelemetryRecord
from src.engine.shell.drone_repository import DroneLedgerRepository

# 원장에 사전 텔레메트리 이력이 없을 때 적용하는 기본 비상 페일세이프 기준값
DEFAULT_FAILSAFE_LATITUDE: float = 37.5665
DEFAULT_FAILSAFE_LONGITUDE: float = 126.9780
DEFAULT_FAILSAFE_BATTERY_PERCENT: int = 100


@dataclass(frozen=True)
class FailsafeResult:
    """비상 감찰 및 페일세이프 전이 결과 봉투."""
    drone_id: str
    is_timeout: bool
    is_recorded: bool
    status: DroneStatus
    elapsed_seconds: float
    alert_code: str


class DroneFailsafeService:
    """드론 페일세이프 오케스트레이션 서비스."""

    def __init__(self, repository: DroneLedgerRepository) -> None:
        self._repository = repository
        self._last_heartbeats: Dict[str, float] = {}

    def record_heartbeat(self, drone_id: str, timestamp: float) -> None:
        """드론의 최신 하트비트 시각을 기록합니다."""
        self._last_heartbeats[drone_id] = timestamp

    def get_last_heartbeat(self, drone_id: str) -> Optional[float]:
        """특정 드론의 마지막 하트비트 시각을 조회합니다."""
        return self._last_heartbeats.get(drone_id)

    def check_drone_failsafe(self, drone_id: str, current_time: float) -> FailsafeResult:
        """특정 드론의 하트비트 타임아웃을 감찰하고 멱등하게 RTH를 발령합니다."""
        last_time = self._last_heartbeats.get(drone_id, current_time)
        latest_record = self._repository.get_latest(drone_id)
        current_status = DroneStatus(latest_record.status) if latest_record else DroneStatus.IDLE

        # Pure Core 판정 위임 (외부 I/O 0건)
        eval_result = evaluate_heartbeat_timeout(
            last_heartbeat_time=last_time,
            current_time=current_time,
            current_status=current_status,
        )

        if not eval_result.should_transition:
            return FailsafeResult(
                drone_id=drone_id,
                is_timeout=eval_result.is_timeout,
                is_recorded=False,
                status=current_status,
                elapsed_seconds=eval_result.elapsed_seconds,
                alert_code=eval_result.alert_code,
            )

        # 멱등성 가드: 이미 원장에 EMERGENCY_RTH 상태로 기록되어 있다면 중복 적재 방어
        if latest_record and latest_record.status == DroneStatus.EMERGENCY_RTH.value:
            return FailsafeResult(
                drone_id=drone_id,
                is_timeout=True,
                is_recorded=False,  # 중복 원장 적재 0건 차단
                status=DroneStatus.EMERGENCY_RTH,
                elapsed_seconds=eval_result.elapsed_seconds,
                alert_code=eval_result.alert_code,
            )

        # 신규 EMERGENCY_RTH 강제 전이 레코드 원장 영구 적재
        lat = latest_record.latitude if latest_record else DEFAULT_FAILSAFE_LATITUDE
        lon = latest_record.longitude if latest_record else DEFAULT_FAILSAFE_LONGITUDE
        alt = latest_record.altitude if latest_record else 0.0
        spd = latest_record.speed if latest_record else 0.0
        bat = latest_record.battery if latest_record else DEFAULT_FAILSAFE_BATTERY_PERCENT

        rth_record = TelemetryRecord(
            drone_id=drone_id,
            latitude=lat,
            longitude=lon,
            altitude=alt,
            speed=spd,
            battery=bat,
            status=DroneStatus.EMERGENCY_RTH.value,
            timestamp=str(current_time),
        )
        self._repository.append(rth_record)

        return FailsafeResult(
            drone_id=drone_id,
            is_timeout=True,
            is_recorded=True,
            status=DroneStatus.EMERGENCY_RTH,
            elapsed_seconds=eval_result.elapsed_seconds,
            alert_code=eval_result.alert_code,
        )
