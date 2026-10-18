# -*- coding: utf-8 -*-
"""하트비트 및 페일세이프 라우터 (Failsafe Routes).

[09 백본 표준] B1 단일 봉투 규격 및 B2 DTO 살균 통신 계약 준수.
3초 이상 통신 두절(LOST) 감지 및 비상 RTH 발령 API.
"""
import time
from fastapi import APIRouter

from src.engine.shell.failsafe_dto import HeartbeatIn, FailsafeCheckIn
from src.engine.shell.drone_failsafe_service import DroneFailsafeService
from src.engine.shell.drone_repository import SqliteDroneLedgerRepository

router = APIRouter(prefix="/api", tags=["failsafe"])

_default_failsafe_repo = SqliteDroneLedgerRepository()
_default_failsafe_service = DroneFailsafeService(repository=_default_failsafe_repo)


def get_failsafe_service() -> DroneFailsafeService:
    """페일세이프 서비스 팩토리 함수."""
    return _default_failsafe_service


@router.post("/heartbeat")
def receive_heartbeat(payload: HeartbeatIn):
    """드론 하트비트 수신 엔드포인트 (B1 단일 봉투)."""
    service = get_failsafe_service()
    service.record_heartbeat(payload.drone_id, payload.timestamp)
    return {
        "success": True,
        "data": {
            "drone_id": payload.drone_id,
            "status": "HEARTBEAT_ACK",
            "received_at": payload.timestamp,
        },
        "error": None,
    }


@router.post("/failsafe/check")
def check_failsafe(payload: FailsafeCheckIn):
    """특정 드론의 통신 상태 감찰 및 비상 귀환 판정 엔드포인트 (B1 단일 봉투)."""
    service = get_failsafe_service()
    check_time = payload.current_time if payload.current_time is not None else time.time()
    result = service.check_drone_failsafe(payload.drone_id, check_time)

    return {
        "success": True,
        "data": {
            "drone_id": result.drone_id,
            "is_lost": result.is_timeout,
            "is_recorded": result.is_recorded,
            "status": result.status.value,
            "elapsed_seconds": result.elapsed_seconds,
            "alert_code": result.alert_code,
        },
        "error": None,
    }
