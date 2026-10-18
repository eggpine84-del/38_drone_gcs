# -*- coding: utf-8 -*-
# [파일명]: geofence_routes.py
# [목적]: 지오펜스 감찰 엔드포인트 (09 백본 B1 단일 봉투 규격 준수)
from typing import Any
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from src.features.geofence.shell.geofence_dto import GeofenceCheckRequest
from src.features.geofence.shell.geofence_service import GeofenceService

router = APIRouter(prefix="/api/features/geofence", tags=["Geofence"])
_default_service = GeofenceService()


def get_geofence_service() -> GeofenceService:
    """서비스 주입 팩토리."""
    return _default_service


@router.post("/check")
def check_geofence(req: GeofenceCheckRequest) -> Any:
    """지오펜스 및 NFZ 침범 감찰 엔드포인트 (B1 단일 봉투 계약)."""
    service = get_geofence_service()
    data = service.check_and_enforce(req)
    return {
        "success": True,
        "data": data,
        "error": None,
    }
