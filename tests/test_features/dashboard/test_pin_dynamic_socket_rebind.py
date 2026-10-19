# -*- coding: utf-8 -*-
"""MAVLink 통신 소켓 재연결 시 비행 명령 서비스 최신 소켓 동적 갱신 핀-테스트."""
from unittest.mock import MagicMock
from src.features.dashboard.shell.command_dto import DroneCommandIn
from src.features.dashboard.shell.flight_command_service import FlightCommandService


def test_pin_dynamic_socket_rebind_and_dispatch():
    """소켓 재연결 시 set_connection을 통해 새 소켓으로 명령이 송출되는지 검증."""
    old_conn = MagicMock()
    new_conn = MagicMock()

    service = FlightCommandService(connection=old_conn)
    assert service.connection is old_conn

    # 소켓 재연결 발생
    service.set_connection(new_conn)
    assert service.connection is new_conn

    cmd = DroneCommandIn(drone_id="DRONE-01", command="ARM", param1=1.0)
    service.dispatch_command(cmd)

    # 이전 죽은 소켓은 호출되지 않고 새 소켓만 호출됨
    assert old_conn.mav.command_long_send.call_count == 0
    assert new_conn.mav.command_long_send.call_count == 1
