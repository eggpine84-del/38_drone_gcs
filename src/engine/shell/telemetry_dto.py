"""텔레메트리 입력 규격 DTO (Telemetry Input DTO).

[09 백본 표준] B2 규격 및 화이트리스트 강제(extra='forbid').
미정의 필드 유입 시 즉시 422 Fail-Fast 차단.
"""

from pydantic import BaseModel, ConfigDict, Field

from src.engine.core.drone_state_machine import DroneStatus


class TelemetryIn(BaseModel):
    """단발 텔레메트리 수신 화이트리스트 규격 DTO."""

    model_config = ConfigDict(extra="forbid")

    drone_id: str = Field(..., min_length=1, description="드론 고유 식별자")
    latitude: float = Field(..., ge=-90.0, le=90.0, description="위도 (-90 ~ +90)")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="경도 (-180 ~ +180)")
    altitude: float = Field(..., description="고도 (m)")
    speed: float = Field(..., description="비행 속도 (m/s)")
    battery: int = Field(..., ge=0, le=100, description="배터리 잔량 (0~100%)")
    target_status: DroneStatus = Field(..., description="요청 비행 상태")
    timestamp: str = Field(..., min_length=1, description="ISO-8601 UTC 타임스탬프")
