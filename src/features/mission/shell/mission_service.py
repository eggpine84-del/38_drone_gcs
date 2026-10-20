# -*- coding: utf-8 -*-
# [파일명]: mission_service.py
# [목적]: 비행 명령 조율 및 원장 상태 전이 적재 Shell 서비스
from datetime import datetime, timezone
from typing import Any, Optional, Tuple

from src.features.mission.core.mission_core import (
    calculate_waypoint_progress,
    evaluate_command,
)
from src.features.mission.shell.mission_dto import CommandRequest, MissionProgressRequest
from src.engine.core.telemetry_record import TelemetryRecord
from src.engine.shell.drone_repository import DroneLedgerRepository, SqliteDroneLedgerRepository

# 원장에 사전 텔레메트리 이력이 없을 때 적용하는 기본 미션 기준값
DEFAULT_MISSION_LATITUDE: float = 37.5665
DEFAULT_MISSION_LONGITUDE: float = 126.9780
DEFAULT_MISSION_BATTERY_PERCENT: int = 100


class MissionService:
    """비행 명령 선행 검증 및 원장 상태 전이 적재 Shell 서비스."""

    def __init__(self, repository: Optional[DroneLedgerRepository] = None) -> None:
        self._repo = repository or SqliteDroneLedgerRepository()

    def execute_command(self, req: CommandRequest) -> Tuple[bool, Optional[dict[str, Any]], Optional[str]]:
        """선행 상태 검증 통과 시에만 명령을 하달하고 원장에 불변 기록."""
        latest = self._repo.get_latest(req.drone_id)
        current_status = latest.status if latest else "IDLE"
        battery = latest.battery if latest else DEFAULT_MISSION_BATTERY_PERCENT

        result = evaluate_command(
            current_status=current_status,
            command=req.command,
            battery=battery,
        )

        if not result.is_allowed:
            return False, None, result.reason

        assert result.next_status is not None

        # 상태 전이 승인 시 원장에 감사 레코드 영구 적재 (Append-Only)
        now_iso = datetime.now(timezone.utc).isoformat()
        lat = latest.latitude if latest else DEFAULT_MISSION_LATITUDE
        lon = latest.longitude if latest else DEFAULT_MISSION_LONGITUDE
        alt = latest.altitude if latest else 0.0
        spd = latest.speed if latest else 0.0

        # TAKEOFF 명령 시 기본 비행 고도 10m 설정
        if result.next_status == "TAKEOFF" and alt == 0.0:
            alt = 10.0

        new_record = TelemetryRecord(
            drone_id=req.drone_id,
            latitude=lat,
            longitude=lon,
            altitude=alt,
            speed=spd,
            battery=battery,
            status=result.next_status,
            timestamp=now_iso,
        )
        saved = self._repo.append(new_record)

        return True, {
            "record_id": saved.id,
            "drone_id": req.drone_id,
            "command": req.command.upper(),
            "previous_status": current_status,
            "next_status": result.next_status,
            "timestamp": saved.timestamp,
        }, None

    def track_progress(self, req: MissionProgressRequest) -> dict[str, Any]:
        """현재 좌표와 웨이포인트 목록 기반 진행률 계산."""
        wp_dicts = [w.model_dump() for w in req.waypoints]
        res = calculate_waypoint_progress(
            current_lat=req.current_latitude,
            current_lon=req.current_longitude,
            current_alt=req.current_altitude,
            waypoints=wp_dicts,
            current_index=req.current_waypoint_index,
        )
        return {
            "drone_id": req.drone_id,
            "current_index": res.current_index,
            "total_count": res.total_count,
            "progress_pct": res.progress_pct,
            "is_completed": res.is_completed,
        }
