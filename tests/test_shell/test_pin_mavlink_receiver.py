# -*- coding: utf-8 -*-
"""MAVLink 셸 수신 어댑터 핀-테스트 (Shell Pin-Test).

네트워크/시리얼 I/O 모의 객체(Mock)를 주입하여 DroneGCSService 단일 원장 적재를 검증.
"""
import pytest
from src.engine.core.drone_state_machine import DroneStatus
from src.engine.shell.drone_gcs_service import DroneGCSService
from src.engine.shell.drone_repository import InMemoryDroneLedgerRepository
from src.engine.shell.mavlink_receiver import MAVLinkReceiver


class DummyMAVMessage:
    """테스트용 MAVLink 패킷 모의 객체."""
    def __init__(self, msg_type: str, fields: dict):
        self._msg_type = msg_type
        for k, v in fields.items():
            setattr(self, k, v)

    def get_type(self) -> str:
        return self._msg_type

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if not k.startswith("_")}


class DummyMAVConnection:
    """테스트용 MAVLink 연결 모의 객체."""
    def __init__(self, messages: list):
        self._messages = list(messages)
        self.target_system = 1
        self.closed = False

    def recv_msg(self):
        if self._messages:
            return self._messages.pop(0)
        return None

    def close(self):
        self.closed = True


def test_1_receiver_processes_mavlink_packets_into_repository():
    """모의 패킷 스트림 수신 후 DroneGCSService를 통해 불변 원장에 적재되는지 검증."""
    repo = InMemoryDroneLedgerRepository()
    service = DroneGCSService(repo)

    # 1. 모의 MAVLink 패킷 큐 준비
    packets = [
        DummyMAVMessage("HEARTBEAT", {"base_mode": 128, "custom_mode": 4, "system_status": 4}),
        DummyMAVMessage("BATTERY_STATUS", {"battery_remaining": 92}),
        DummyMAVMessage(
            "GLOBAL_POSITION_INT",
            {"lat": 375665000, "lon": 1269780000, "relative_alt": 0, "vx": 0, "vy": 0},
        ),
    ]
    mock_conn = DummyMAVConnection(packets)

    receiver = MAVLinkReceiver(
        drone_id="DRONE-SITL-1",
        service=service,
        connection=mock_conn,
    )

    # 2. 패킷 1회 순회 소비
    processed_count = receiver.poll_once()

    # 3. GLOBAL_POSITION_INT 수신 시점에 IngestPayload로 포장되어 적재되었는지 검증
    assert processed_count >= 1
    latest = service.get_latest_telemetry("DRONE-SITL-1")
    assert latest is not None
    assert latest.drone_id == "DRONE-SITL-1"
    assert pytest.approx(latest.latitude, rel=1e-5) == 37.5665
    assert pytest.approx(latest.longitude, rel=1e-5) == 126.9780
    assert pytest.approx(latest.altitude, rel=1e-5) == 0.0
    assert latest.battery == 92
    assert latest.status == DroneStatus.ARMED.value


def test_2_receiver_handles_empty_queue_without_blocking():
    """패킷이 없는 상태에서 블로킹 없이 0 반환 및 정상 통과하는지 검증."""
    repo = InMemoryDroneLedgerRepository()
    service = DroneGCSService(repo)
    mock_conn = DummyMAVConnection([])

    receiver = MAVLinkReceiver(
        drone_id="DRONE-SITL-1",
        service=service,
        connection=mock_conn,
    )

    processed_count = receiver.poll_once()
    assert processed_count == 0
    assert service.get_latest_telemetry("DRONE-SITL-1") is None
