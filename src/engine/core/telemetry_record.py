"""텔레메트리 원장 불변 엔티티 (Telemetry Record SSOT).

CONSTITUTION.md 제2조 최소 데이터 스키마 규격을 100% 충족하는 순수 불변 데이터 클래스.
외부 I/O 0건, Side-Effect 0건.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class TelemetryRecord:
    """원장에 영구 보존되는 단일 텔레메트리 불변 레코드 (SSOT)."""

    drone_id: str
    latitude: float
    longitude: float
    altitude: float
    speed: float
    battery: int
    status: str
    timestamp: str
    id: int | None = None

    def __post_init__(self) -> None:
        """데이터 무결성 가드 (공리 1)."""
        if not self.drone_id or not self.drone_id.strip():
            raise ValueError("drone_id는 비어 있거나 공백일 수 없습니다.")
        if not (-90.0 <= self.latitude <= 90.0):
            raise ValueError("latitude는 -90.0 ~ +90.0 범위 내여야 합니다.")
        if not (-180.0 <= self.longitude <= 180.0):
            raise ValueError("longitude는 -180.0 ~ +180.0 범위 내여야 합니다.")
        if self.altitude < 0.0:
            raise ValueError("altitude는 음수가 될 수 없습니다.")
        if self.speed < 0.0:
            raise ValueError("speed는 음수가 될 수 없습니다.")
        if not (0 <= self.battery <= 100):
            raise ValueError("battery는 0~100 범위 내여야 합니다.")
