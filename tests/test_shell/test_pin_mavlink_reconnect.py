# -*- coding: utf-8 -*-
"""MAVLink 통신 단절 시 무소음 자동 재연결(Auto-Reconnect) 핀-테스트.

소켓 단절(EOF/에러) 발생 시 안전 자원 폐기 및 쿨다운 후 자동 재연결 라이프사이클을 검증.
"""
import time
from unittest.mock import MagicMock
import pytest

from src.engine.shell.drone_gcs_service import DroneGCSService
from src.engine.shell.drone_repository import InMemoryDroneLedgerRepository
from src.engine.shell.mavlink_receiver import MAVLinkReceiver


class BrokenMAVConnection:
    """소켓 단절(EOF/예외)을 일으키는 모의 커넥션."""
    def __init__(self, fail_with_exception: bool = False):
        self.closed = False
        self.fail_with_exception = fail_with_exception

    def recv_msg(self):
        if self.fail_with_exception:
            raise ConnectionResetError("Connection closed by remote host")
        # pymavlink의 TCP EOF 동작 모사 (소켓이 닫혔을 때)
        return None

    def close(self):
        self.closed = True


def test_1_receiver_detects_disconnect_and_triggers_safe_reconnect():
    """소켓 예외/단절 발생 시 is_connected=False로 전환되고 자동 재연결이 수행되는지 검증."""
    repo = InMemoryDroneLedgerRepository()
    service = DroneGCSService(repo)
    broken_conn = BrokenMAVConnection(fail_with_exception=True)

    receiver = MAVLinkReceiver(
        drone_id="TEST-RECONNECT-1",
        service=service,
        connection=broken_conn,
        connection_string="tcp:127.0.0.1:5762",
    )

    # 1. 초기 연결 상태 확인
    assert receiver.is_connected is True

    # 2. 예외 발생 시 소켓이 닫히고 is_connected=False로 전환되어야 함
    receiver.poll_once()
    assert receiver.is_connected is False
    assert broken_conn.closed is True

    # 3. 재연결 쿨다운(1.0초) 이전에는 재연결을 시도하지 않아야 함
    receiver.poll_once()
    assert receiver.is_connected is False

    # 4. 재연결 쿨다운 경과 후 정상 새 커넥션으로 복구되는지 검증
    # _init_connection을 모킹하여 새 커넥션 주입
    new_mock_conn = MagicMock()
    new_mock_conn.recv_msg.return_value = None

    receiver._reconnect_interval = 0.05  # 테스트용 짧은 쿨다운
    time.sleep(0.06)

    receiver._init_connection = MagicMock(side_effect=lambda conn_str: setattr(receiver, "_connection", new_mock_conn) or setattr(receiver, "_is_connected", True))
    receiver.poll_once()

    assert receiver._init_connection.called
    assert receiver.is_connected is True
