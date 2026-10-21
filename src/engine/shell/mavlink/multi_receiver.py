"""MAVLink 복수 포트/다중 기체 동시 리스닝 오케스트레이터 (Multi-Receiver).

단일 포트 SysID 자동 분류 및 복수 포트 동시 리스닝을 총괄하는 서브모듈입니다.
단일 책임 원칙(SRP)에 따라 mavlink 서브패키지로 격리되었습니다.
"""

from typing import Any

from src.engine.shell.drone_gcs_service import DroneGCSService
from src.engine.shell.mavlink.receiver import MAVLinkReceiver


class MAVLinkMultiReceiver:
    """복수 포트(다중 연결) 및 다중 기체 동시 리스닝 오케스트레이터."""

    def __init__(
        self,
        service: DroneGCSService,
        connections: list[Any] | None = None,
        connection_strings: list[str] | None = None,
        default_drone_id: str = "DRONE-01",
        auto_detect_sysid: bool = True,
    ) -> None:
        """다중 포트 수신기 초기화.

        Args:
            service: GCS 서비스 단일 진실 공급원.
            connections: 사전 생성된 연결 객체 목록 (테스트/DI).
            connection_strings: 연결 문자열 리스트.
            default_drone_id: 폴백 기체 ID.
            auto_detect_sysid: SysID 자동 분류 활성화 여부.
        """
        self._service = service
        self._receivers: list[MAVLinkReceiver] = []

        if connections:
            for conn in connections:
                self._receivers.append(
                    MAVLinkReceiver(
                        drone_id=default_drone_id,
                        service=service,
                        connection=conn,
                        auto_detect_sysid=auto_detect_sysid,
                    )
                )
            return

        for conn_str in connection_strings or []:
            self._receivers.append(
                MAVLinkReceiver(
                    drone_id=default_drone_id,
                    service=service,
                    connection_string=conn_str,
                    auto_detect_sysid=auto_detect_sysid,
                )
            )

    @property
    def connection(self) -> Any:
        """기본(첫 번째) 활성 통신 연결 객체를 반환합니다."""
        return self._receivers[0].connection if self._receivers else None

    @property
    def is_connected(self) -> bool:
        """하나 이상의 수신기가 연결되어 있는지 여부를 반환합니다."""
        return any(r.is_connected for r in self._receivers)

    def poll_once(self) -> int:
        """등록된 모든 하위 수신기를 1회 순회 소비하여 총 적재 건수를 반환합니다."""
        total = 0
        for r in self._receivers:
            total += r.poll_once()
        return total

    def close(self) -> None:
        """모든 하위 수신기를 안전하게 회수합니다."""
        for r in self._receivers:
            r.close()
