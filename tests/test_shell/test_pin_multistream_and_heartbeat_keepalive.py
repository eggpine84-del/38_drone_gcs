# -*- coding: utf-8 -*-
"""ArduPilot 멀티 데이터 스트림 요청 및 하트비트 기반 활성 기체 보존 핀-테스트."""
import pytest
from src.engine.shell.drone_gcs_service import DroneGCSService
from src.engine.shell.drone_repository import InMemoryDroneLedgerRepository
from src.engine.shell.mavlink.receiver import MAVLinkReceiver


class MockMultiStreamProtocol:
    def __init__(self):
        self.sent_heartbeats = []
        self.sent_stream_requests = []

    def heartbeat_send(self, *args, **kwargs):
        self.sent_heartbeats.append(args)

    def request_data_stream_send(self, target_sys, target_comp, stream_id, rate, start):
        self.sent_stream_requests.append({
            "target_sys": target_sys,
            "target_comp": target_comp,
            "stream_id": stream_id,
            "rate": rate,
            "start": start,
        })


class MockConnectionForStream:
    def __init__(self):
        self.mav = MockMultiStreamProtocol()
        self.target_system = 1
        self.target_component = 1

    def recv_msg(self):
        return None

    def close(self):
        pass


def test_receiver_requests_all_critical_ardupilot_streams():
    """ArduPilot 최신 펌웨어에서 침묵을 방어하기 위해 POSITION(6), EXTRA1/2(10,11), EXT_STATUS(2) 등 필수 4대 스트림을 전수 요청하는지 검증."""
    repo = InMemoryDroneLedgerRepository()
    service = DroneGCSService(repo)
    conn = MockConnectionForStream()

    receiver = MAVLinkReceiver(
        drone_id="DRONE-01",
        service=service,
        connection=conn,
    )

    receiver.poll_once()

    requested_stream_ids = {r["stream_id"] for r in conn.mav.sent_stream_requests}

    # ArduPilot 필수 스트림 ID 검증:
    stream_all = 0
    stream_pos = 6
    assert (stream_all in requested_stream_ids), "MAV_DATA_STREAM_ALL 누락"
    assert (stream_pos in requested_stream_ids), "MAV_DATA_STREAM_POSITION 누락 (GPS/고도 침묵 원인)"
    assert (2 in requested_stream_ids), "MAV_DATA_STREAM_EXTENDED_STATUS 누락"
    assert (10 in requested_stream_ids), "MAV_DATA_STREAM_EXTRA1 누락"
    assert (11 in requested_stream_ids), "MAV_DATA_STREAM_EXTRA2 누락"


class MockMsg:
    def __init__(self, msg_type, data, src_sys=1):
        self._type = msg_type
        self._data = data
        self._src_sys = src_sys

    def get_type(self):
        return self._type

    def to_dict(self):
        return self._data

    def get_srcSystem(self):
        return self._src_sys


class MockQueuedConnection:
    def __init__(self, queue):
        self.mav = MockMultiStreamProtocol()
        self.target_system = 1
        self.target_component = 1
        self._queue = list(queue)

    def recv_msg(self):
        return self._queue.pop(0) if self._queue else None

    def close(self):
        pass


def test_receiver_heartbeat_keeps_telemetry_fresh_with_last_gps():
    """GPS 패킷 주기가 늦어지더라도 HEARTBEAT 수신 시 이전 위치를 재사용하여 텔레메트리를 지속 갱신(Keep-Alive)하는지 검증."""
    repo = InMemoryDroneLedgerRepository()
    service = DroneGCSService(repo)

    gps_dict = {"lat": 375665000, "lon": 1269780000, "relative_alt": 0, "vx": 0, "vy": 0}
    hb_idle = {"base_mode": 81, "custom_mode": 0}
    hb_armed = {"base_mode": 89 | 128, "custom_mode": 4}  # ARMED + GUIDED

    # 1. 최초 GPS + IDLE 하트비트
    q1 = [
        MockMsg("HEARTBEAT", hb_idle),
        MockMsg("GLOBAL_POSITION_INT", gps_dict),
    ]
    conn1 = MockQueuedConnection(q1)
    recv = MAVLinkReceiver(drone_id="DRONE-01", service=service, connection=conn1)
    cnt1 = recv.poll_once()
    assert cnt1 == 1

    # 2. GPS 없이 하트비트(ARMED)만 유입되었을 때
    q2 = [
        MockMsg("HEARTBEAT", hb_armed),
    ]
    recv._connection = MockQueuedConnection(q2)
    # 강제로 이전 적재 쿨다운 경과
    recv._drone_last_ingest_time["DRONE-01"] = 0.0

    cnt2 = recv.poll_once()
    assert cnt2 >= 1, "HEARTBEAT 단독 수신 시 이전 GPS 좌표를 활용한 갱신 적재 실패"

    latest = repo.get_latest("DRONE-01")
    assert latest is not None
    assert latest.status == "ARMED"


