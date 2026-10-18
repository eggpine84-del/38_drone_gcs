# -*- coding: utf-8 -*-
# [파일명]: mission_dto.py
# [목적]: 비행 명령 및 미션 진행률 살균 DTO (09 백본 B2 extra='forbid' 헌법 준수)
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class CommandRequest(BaseModel):
    """비행 명령 하달 요청 DTO."""
    model_config = ConfigDict(extra="forbid")

    drone_id: str = Field(..., min_length=1, max_length=50)
    command: str = Field(..., min_length=2, max_length=20)


class WaypointItemDTO(BaseModel):
    """웨이포인트 단일 항목 DTO."""
    model_config = ConfigDict(extra="forbid")

    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    altitude: float = Field(..., ge=0.0, le=500.0)


class MissionProgressRequest(BaseModel):
    """미션 진행률 계산 요청 DTO."""
    model_config = ConfigDict(extra="forbid")

    drone_id: str = Field(..., min_length=1, max_length=50)
    current_latitude: float = Field(..., ge=-90.0, le=90.0)
    current_longitude: float = Field(..., ge=-180.0, le=180.0)
    current_altitude: float = Field(..., ge=0.0, le=500.0)
    current_waypoint_index: int = Field(default=0, ge=0)
    waypoints: List[WaypointItemDTO] = Field(..., min_length=1)
