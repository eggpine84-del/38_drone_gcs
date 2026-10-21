"""대시보드 비행 명령 DTO 스키마 (B2 DTO 살균 헌법 준수)."""

from pydantic import BaseModel, ConfigDict, Field, field_validator

VALID_COMMANDS = {
    "ARM",
    "DISARM",
    "TAKEOFF",
    "HOLD",
    "LOITER",
    "GUIDED",
    "RTL",
    "LAND",
    "MOVE",
    "GIMBAL",
    "KILL",
    "SET_MODE",
    "DROP",
}


class DroneCommandIn(BaseModel):
    """비행 제어 명령 입력 스키마."""

    model_config = ConfigDict(extra="forbid")
    drone_id: str = Field(
        ..., min_length=1, max_length=64, description="관제 대상 드론 식별자"
    )
    command: str = Field(
        ..., min_length=2, max_length=32, description="비행 제어 명령 코드"
    )
    param1: float = Field(
        0.0, description="명령 파라미터 1 (고도, 시동플래그, 전진속도 등)"
    )
    param2: float = Field(0.0, description="명령 파라미터 2 (우측속도, 짐벌피치 등)")
    param3: float = Field(0.0, description="명령 파라미터 3 (수직속도 등)")
    param4: float = Field(0.0, description="명령 파라미터 4 (추가 파라미터)")

    @field_validator("drone_id")
    @classmethod
    def validate_drone_id(cls, v: str) -> str:
        clean = v.strip()
        if not clean:
            raise ValueError("드론 ID는 공백일 수 없습니다.")
        return clean

    @field_validator("command")
    @classmethod
    def validate_command(cls, v: str) -> str:
        clean = v.strip().upper()
        if clean not in VALID_COMMANDS:
            raise ValueError(f"지원하지 않는 비행 명령입니다: {clean}")
        return clean
