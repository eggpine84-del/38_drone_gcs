# -*- coding: utf-8 -*-
"""단발 텔레메트리 수신 라우터 (Telemetry Ingest Router).

[09 백본 표준] B1 단일 봉투 규격 및 B2 DTO 살균 통신 계약 준수.
0.001초 응답 SLA 보장.
"""
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from src.engine.shell.telemetry_dto import TelemetryIn
from src.engine.shell.drone_gcs_service import DroneGCSService, IngestPayload
from src.engine.shell.drone_repository import SqliteDroneLedgerRepository

router = APIRouter(prefix="/api", tags=["telemetry"])

# 단일 기본 서비스 인스턴스 (SQLite 원장 연동)
_default_repository = SqliteDroneLedgerRepository()
_default_service = DroneGCSService(repository=_default_repository)


def get_service() -> DroneGCSService:
    """서비스 의존성 팩토리 함수."""
    return _default_service


@router.post("/telemetry")
def ingest_telemetry(payload: TelemetryIn):
    """단발 텔레메트리 수신 및 4대 공리 검증 엔드포인트 (B1 단일 봉투)."""
    service = get_service()
    ingest_payload = IngestPayload(
        drone_id=payload.drone_id,
        latitude=payload.latitude,
        longitude=payload.longitude,
        altitude=payload.altitude,
        speed=payload.speed,
        battery=payload.battery,
        target_status=payload.target_status,
        timestamp=payload.timestamp,
    )
    result = service.process_telemetry(ingest_payload)

    if not result.success:
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "data": None,
                "error": {
                    "code": "TRANSITION_REJECTED",
                    "message": result.reason,
                    "violations": list(result.violations),
                },
            },
        )

    assert result.record is not None
    return {
        "success": True,
        "data": {
            "record_id": result.record.id,
            "drone_id": result.record.drone_id,
            "status": result.record.status,
            "is_failsafe_forced": result.is_failsafe_forced,
            "timestamp": result.record.timestamp,
        },
        "error": None,
    }
