# [파일명]: mission_routes.py
# [목적]: 비행 명령 제어 및 웨이포인트 진행률 엔드포인트 (09 백본 B1 단일 봉투 규격)
from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from src.features.mission.shell.mission_dto import (
    CommandRequest,
    MissionProgressRequest,
)
from src.features.mission.shell.mission_service import MissionService

router = APIRouter(prefix="/api/features/mission", tags=["Mission"])
_default_service = MissionService()


def get_mission_service() -> MissionService:
    """서비스 주입 팩토리."""
    return _default_service


@router.post("/command")
def post_flight_command(req: CommandRequest) -> Any:
    """비행 명령 하달 및 선행 상태 검증 엔드포인트 (B1 단일 봉투)."""
    service = get_mission_service()
    success, data, reason = service.execute_command(req)

    if not success:
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "data": None,
                "error": {
                    "code": "COMMAND_REJECTED",
                    "message": reason,
                },
            },
        )

    return {
        "success": True,
        "data": data,
        "error": None,
    }


@router.post("/progress")
def post_mission_progress(req: MissionProgressRequest) -> Any:
    """웨이포인트 미션 실시간 진행률 계산 엔드포인트 (B1 단일 봉투)."""
    service = get_mission_service()
    data = service.track_progress(req)
    return {
        "success": True,
        "data": data,
        "error": None,
    }
