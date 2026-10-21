"""하트비트 및 페일세이프 DTO 규격 (Failsafe DTO).

[09 백본 표준] B2 규격 및 화이트리스트 강제(extra='forbid').
미정의 필드 유입 시 즉시 422 Fail-Fast 차단.
"""

from pydantic import BaseModel, ConfigDict, Field


class HeartbeatIn(BaseModel):
    """하트비트 수신 화이트리스트 규격 DTO."""

    model_config = ConfigDict(extra="forbid")

    drone_id: str = Field(..., min_length=1, description="드론 고유 식별자")
    timestamp: float = Field(..., description="하트비트 에포크 초 타임스탬프")


class FailsafeCheckIn(BaseModel):
    """비상 감찰 화이트리스트 규격 DTO."""

    model_config = ConfigDict(extra="forbid")

    drone_id: str = Field(..., min_length=1, description="드론 고유 식별자")
    current_time: float | None = Field(
        None, description="감찰 기준 시각 (생략 시 서버 현재시각)"
    )
