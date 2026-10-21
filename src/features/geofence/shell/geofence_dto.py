# [파일명]: geofence_dto.py
# [목적]: 지오펜스 감찰 요청/응답 살균 DTO (09 백본 B2 extra='forbid' 헌법 준수)
from pydantic import BaseModel, ConfigDict, Field


class NFZCircleDTO(BaseModel):
    """비행 금지 구역(NFZ) 원형 모델."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1, max_length=100)
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    radius_meters: float = Field(..., gt=0.0)


class GeofenceCheckRequest(BaseModel):
    """지오펜스 감찰 요청 DTO (허가되지 않은 임의 필드 유입 시 자동 거부)."""

    model_config = ConfigDict(extra="forbid")

    drone_id: str = Field(..., min_length=1, max_length=50)
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    allowed_polygon: list[list[float]] | None = Field(default=None)
    nfz_list: list[NFZCircleDTO] | None = Field(default=None)
