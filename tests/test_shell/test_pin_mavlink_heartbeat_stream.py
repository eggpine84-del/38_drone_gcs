# -*- coding: utf-8 -*-
"""MAVLink GCS 능동 하트비트 및 데이터 스트림 요청 회로 핀-테스트 (Shell Pin-Test).

GCS 연결 시 FCU(ArduPilot/PX4)로 MAVLink HEARTBEAT 및 REQUEST_DATA_STREAM_ALL 패킷을
주기적(1초 주기)으로 자동 송출하여 외부 GCS 없이도 텔레메트리 스트림이 개방되는지 검증합니다.
"""
import time
import pytest
from src.engine.shell.drone_gcs_service import DroneGCSService
from src.engine.shell.drone_repository import InMemoryDroneLedgerRepository
from src.engine.shell.mavlink_receiver import MAVLinkReceiver


class MockMAVLinkProtocol:
    """테스트용 pymavlink.mav 모의 송신 객체."""

    def __init__(self) -> None:
        self.sent_heartbeats = []
        self.sent_stream_requests = []

    def heartbeat_send(
        self,
        mav_type: int,
        autopilot: int,
        base_mode: int,
        custom_mode: int,
        system_status: int,
    ) -> None:
        self.sent_heartbeats.append(
            {
                "type": mav_type,
                "autopilot": autopilot,
                "base_mode": base_mode,
                "custom_mode": custom_mode,
                "system_status": system_status,
            }
        )

    def request_data_stream_send(
        self,
        target_system: int,
        target_component: int,
        req_stream_id: int,
        req_message_rate: int,
        start_stop: int,
    ) -> None:
        self.sent_stream_requests.append(
            {
                "target_system": target_system,
                "target_component": target_component,
                "req_stream_id": req_stream_id,
                "req_message_rate": req_message_rate,
                "start_stop": start_stop,
            }
        )


class MockMAVConnection:
    """테스트용 pymavlink 연결 모의 객체."""

    def __init__(self) -> None:
        self.mav = MockMAVLinkProtocol()
        self.target_system = 1
        self.target_component = 1
        self.closed = False

    def recv_msg(self):
        return None

    def close(self) -> None:
        self.closed = True


def test_1_receiver_sends_heartbeat_and_stream_request_on_init():
    """MAVLink 연결 객체 주입 및 첫 poll_once 호출 시 GCS 하트비트와 스트림 요청이 발송되는지 검증."""
    repo = InMemoryDroneLedgerRepository()
    service = DroneGCSService(repo)
    mock_conn = MockMAVConnection()

    receiver = MAVLinkReceiver(
        drone_id="DRONE-SITL-1",
        service=service,
        connection=mock_conn,
    )

    receiver.poll_once()

    # 하트비트가 1회 이상 발송되었는지 단언 (GCS 타입 6: MAV_TYPE_GCS)
    assert len(mock_conn.mav.sent_heartbeats) >= 1
    hb = mock_conn.mav.sent_heartbeats[0]
    assert hb["type"] == 6  # MAV_TYPE_GCS

    # 데이터 스트림 요청이 1회 이상 발송되었는지 단언 (전체 스트림 ID 0: MAV_DATA_STREAM_ALL, 4Hz)
    assert len(mock_conn.mav.sent_stream_requests) >= 1
    req = mock_conn.mav.sent_stream_requests[0]
    assert req["req_stream_id"] == 0  # MAV_DATA_STREAM_ALL
    assert req["req_message_rate"] == 4
    assert req["start_stop"] == 1


def test_2_receiver_throttles_heartbeat_within_interval():
    """1초 이내 연속 호출 시 하트비트 중복 전송(패킷 폭풍)이 방지되는지 검증."""
    repo = InMemoryDroneLedgerRepository()
    service = DroneGCSService(repo)
    mock_conn = MockMAVConnection()

    receiver = MAVLinkReceiver(
        drone_id="DRONE-SITL-1",
        service=service,
        connection=mock_conn,
    )

    receiver.poll_once()
    initial_hb_count = len(mock_conn.mav.sent_heartbeats)
    assert initial_hb_count >= 1

    # 1초 이내 재호출 시 추가 발송 없어야 함
    receiver.poll_once()
    receiver.poll_once()
    assert len(mock_conn.mav.sent_heartbeats) == initial_hb_count


def test_3_receiver_resends_heartbeat_after_interval_elapsed():
    """1초 초과 경과 후 poll_once 호출 시 Keep-Alive 하트비트가 재전송되는지 검증."""
    repo = InMemoryDroneLedgerRepository()
    service = DroneGCSService(repo)
    mock_conn = MockMAVConnection()

    receiver = MAVLinkReceiver(
        drone_id="DRONE-SITL-1",
        service=service,
        connection=mock_conn,
    )

    receiver.poll_once()
    assert len(mock_conn.mav.sent_heartbeats) == 1

    # 쿨다운 타임스탬프를 2초 전으로 강제 조작
    receiver._last_heartbeat_sent = time.time() - 2.0

    receiver.poll_once()
    assert len(mock_conn.mav.sent_heartbeats) == 2
