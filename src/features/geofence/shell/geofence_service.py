# [파일명]: geofence_service.py
# [목적]: 지오펜스 감찰 오케스트레이터 및 원장 감사 로그 적재 Shell 서비스
from datetime import UTC, datetime
from typing import Any

from src.engine.core.telemetry_record import TelemetryRecord
from src.engine.shell.drone_repository import (
    DroneLedgerRepository,
    SqliteDroneLedgerRepository,
)
from src.features.geofence.core.geofence_core import evaluate_geofence
from src.features.geofence.shell.geofence_dto import GeofenceCheckRequest

# 원장에 사전 텔레메트리 이력이 없을 때 적용하는 비상 기본값 (Fail-Safe Default: 0% 배터리)
DEFAULT_FAILSAFE_BATTERY_PERCENT: int = 0


class GeofenceService:
    """지오펜스 감찰 및 침범 시 EMERGENCY_RTH 원장 강제 적재 Shell 서비스."""

    def __init__(self, repository: DroneLedgerRepository | None = None) -> None:
        self._repo = repository or SqliteDroneLedgerRepository()

    def check_and_enforce(self, req: GeofenceCheckRequest) -> dict[str, Any]:
        """순수 기하 코어 연산 위임 및 침범 시 원장 영구 적재 (Append-Only)."""
        nfz_dicts = [n.model_dump() for n in req.nfz_list] if req.nfz_list else None

        result = evaluate_geofence(
            drone_id=req.drone_id,
            latitude=req.latitude,
            longitude=req.longitude,
            allowed_polygon=req.allowed_polygon,
            nfz_list=nfz_dicts,
        )

        # 헌법 공리 3항: 침범/이탈 감지 시 즉시 원장에 EMERGENCY_RTH 상태 기록
        if result.is_breached:
            now_iso = datetime.now(UTC).isoformat()
            latest = self._repo.get_latest(req.drone_id)
            alt = latest.altitude if latest else 0.0
            spd = latest.speed if latest else 0.0
            bat = latest.battery if latest else DEFAULT_FAILSAFE_BATTERY_PERCENT

            breach_record = TelemetryRecord(
                drone_id=req.drone_id,
                latitude=req.latitude,
                longitude=req.longitude,
                altitude=alt,
                speed=spd,
                battery=bat,
                status="EMERGENCY_RTH",
                timestamp=now_iso,
            )
            self._repo.append(breach_record)

        return {
            "drone_id": result.drone_id,
            "is_breached": result.is_breached,
            "breach_type": result.breach_type,
            "reason": result.reason,
            "recommended_status": result.recommended_status,
        }
