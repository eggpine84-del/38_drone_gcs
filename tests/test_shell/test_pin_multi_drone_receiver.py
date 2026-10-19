# -*- coding: utf-8 -*-
"""다중 드론(SysID) 및 복수 포트 하이브리드 수신 핀-테스트 (Pin Test Multi Drone Receiver).

FCIS 및 Pin-Test First 원칙:
1. 단일 포트 내 다중 SysID 자동 식별 및 기체별 독립 원장 적재 검증.
2. 기체별 캐시(하트비트/배터리) 상호 간섭 격리 검증.
3. 복수 연결 문자열(다중 포트) 파싱 및 멀티 리시버 오케스트레이션 검증.
4. 비정상 SysID(0, 음수, 256 등) 유입 시 비즈니스 뇌관 방어 검증.
"""
import pytest
from unittest.mock import MagicMock

from src.engine.core.mavlink_parser_core import (
    parse_connection_strings_core,
    resolve_drone_id_from_sysid,
)
from src.engine.shell.db_schema import init_db
from src.engine.shell.drone_gcs_service import DroneGCSService
from src.engine.shell.drone_repository import SqliteDroneLedgerRepository
from src.engine.shell.mavlink_receiver import MAVLinkMultiReceiver, MAVLinkReceiver


class DummyMAVMessage:
    """테스트용 가상 MAVLink 메시지 모의 객체."""

    def __init__(self, msg_type: str, data: dict, src_system: int = 1):
        self._msg_type = msg_type
        self._data = data
        self._src_system = src_system

    def get_type(self) -> str:
        return self._msg_type

    def get_srcSystem(self) -> int:
        return self._src_system

    def to_dict(self) -> dict:
        return dict(self._data)


class DummyMAVConnection:
    """테스트용 가상 pymavlink 연결 객체."""

    def __init__(self, messages: list):
        self._messages = list(messages)

    def recv_msg(self):
        if self._messages:
            return self._messages.pop(0)
        return None

    def close(self):
        pass


@pytest.fixture(autouse=True)
def setup_test_db(tmp_path, monkeypatch):
    """테스트용 임시 SQLite DB 환경 구성."""
    db_file = str(tmp_path / "test_multi_drone.db")
    monkeypatch.setenv("APP_DB_PATH", db_file)
    init_db()
    return db_file


def test_resolve_drone_id_and_connection_strings_core():
    """순수 코어 파서: SysID 식별 및 연결 문자열 파싱 검증."""
    # 1. 정상 SysID 매핑
    assert resolve_drone_id_from_sysid(1) == "DRONE-01"
    assert resolve_drone_id_from_sysid(2) == "DRONE-02"
    assert resolve_drone_id_from_sysid(15) == "DRONE-15"

    # 2. 비정상 돌출값 방어
    assert resolve_drone_id_from_sysid(0) == "DRONE-UNKNOWN"
    assert resolve_drone_id_from_sysid(-5) == "DRONE-UNKNOWN"
    assert resolve_drone_id_from_sysid(300) == "DRONE-UNKNOWN"

    # 3. 연결 문자열 살균 및 중복 제거
    raw_conns = "tcp:127.0.0.1:5760, tcp:127.0.0.1:5762, , tcp:127.0.0.1:5760"
    parsed = parse_connection_strings_core(raw_conns)
    assert parsed == ["tcp:127.0.0.1:5760", "tcp:127.0.0.1:5762"]

    # 4. 공백/빈값 안전 폴백
    assert parse_connection_strings_core("") == ["udpin:0.0.0.0:14550"]
    assert parse_connection_strings_core("   ") == ["udpin:0.0.0.0:14550"]


def test_single_port_multi_sysid_auto_dispatch(setup_test_db):
    """단일 포트 내에서 SysID 1과 SysID 2가 유입될 때 기체별 독립 원장 적재 검증."""
    repo = SqliteDroneLedgerRepository(db_path=setup_test_db)
    service = DroneGCSService(repository=repo)

    messages = [
        # 드론 1 (SysID=1) 하트비트 및 GPS (시동 상태: ARMED)
        DummyMAVMessage("HEARTBEAT", {"base_mode": 128, "custom_mode": 0}, src_system=1),
        DummyMAVMessage(
            "GLOBAL_POSITION_INT",
            {"lat": 375000000, "lon": 1270000000, "relative_alt": 0, "vx": 0, "vy": 0},
            src_system=1,
        ),
        # 드론 2 (SysID=2) 하트비트 및 GPS (시동 상태: ARMED)
        DummyMAVMessage("HEARTBEAT", {"base_mode": 128, "custom_mode": 0}, src_system=2),
        DummyMAVMessage(
            "GLOBAL_POSITION_INT",
            {"lat": 351000000, "lon": 1290000000, "relative_alt": 0, "vx": 0, "vy": 0},
            src_system=2,
        ),
    ]

    mock_conn = DummyMAVConnection(messages)
    receiver = MAVLinkReceiver(
        drone_id="DRONE-01",  # 기본값
        service=service,
        connection=mock_conn,
        auto_detect_sysid=True,
    )

    # 1회 폴링으로 2개 기체 텔레메트리 일괄 처리
    processed = receiver.poll_once()
    assert processed == 2

    # 기체 1 (DRONE-01) 원장 검증
    state_drone1 = repo.get_latest("DRONE-01")
    assert state_drone1 is not None
    assert state_drone1.drone_id == "DRONE-01"
    assert pytest.approx(state_drone1.latitude, 0.0001) == 37.5
    assert pytest.approx(state_drone1.longitude, 0.0001) == 127.0
    assert pytest.approx(state_drone1.altitude, 0.1) == 0.0

    # 기체 2 (DRONE-02) 원장 검증
    state_drone2 = repo.get_latest("DRONE-02")
    assert state_drone2 is not None
    assert state_drone2.drone_id == "DRONE-02"
    assert pytest.approx(state_drone2.latitude, 0.0001) == 35.1
    assert pytest.approx(state_drone2.longitude, 0.0001) == 129.0
    assert pytest.approx(state_drone2.altitude, 0.1) == 0.0


def test_multi_port_mavlink_receiver_orchestration(setup_test_db):
    """복수 포트(다중 연결 문자열) 멀티 리시버 오케스트레이션 검증."""
    repo = SqliteDroneLedgerRepository(db_path=setup_test_db)
    service = DroneGCSService(repository=repo)

    # 2개의 가상 포트 연결
    conn1_messages = [
        DummyMAVMessage("HEARTBEAT", {"base_mode": 128, "custom_mode": 0}, src_system=1),
        DummyMAVMessage(
            "GLOBAL_POSITION_INT",
            {"lat": 371000000, "lon": 1271000000, "relative_alt": 0, "vx": 0, "vy": 0},
            src_system=1,
        ),
    ]
    conn2_messages = [
        DummyMAVMessage("HEARTBEAT", {"base_mode": 128, "custom_mode": 0}, src_system=2),
        DummyMAVMessage(
            "GLOBAL_POSITION_INT",
            {"lat": 362000000, "lon": 1282000000, "relative_alt": 0, "vx": 0, "vy": 0},
            src_system=2,
        ),
    ]

    mock_conn1 = DummyMAVConnection(conn1_messages)
    mock_conn2 = DummyMAVConnection(conn2_messages)

    # MultiPortMAVLinkReceiver에 주입
    multi_receiver = MAVLinkMultiReceiver(
        service=service,
        connections=[mock_conn1, mock_conn2],
        auto_detect_sysid=True,
    )

    assert multi_receiver.is_connected is True

    processed = multi_receiver.poll_once()
    assert processed == 2

    # 각각의 기체 데이터가 독립적으로 적재되었는지 확인
    state1 = repo.get_latest("DRONE-01")
    state2 = repo.get_latest("DRONE-02")
    assert state1 is not None and state1.drone_id == "DRONE-01"
    assert state2 is not None and state2.drone_id == "DRONE-02"

    multi_receiver.close()
    assert multi_receiver.is_connected is False

