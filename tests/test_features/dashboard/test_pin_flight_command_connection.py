# -*- coding: utf-8 -*-
"""웹 대시보드 비행 명령과 MAVLink 통신 소켓 직결 핀-테스트 (Pin-Test).

웹 대시보드에서 전달된 비행 명령이 FlightCommandService에 주입된 MAVLink 소켓을 통해
실제 바이너리 MAVLink 패킷(command_long_send, set_mode_send 등)으로 물리 송출되는지 검증합니다.
"""
import pytest
from src.features.dashboard.shell.command_dto import DroneCommandIn
from src.features.dashboard.shell.flight_command_service import (
    FlightCommandService,
    get_flight_command_service,
)


class MockMAVProtocol:
    """테스트용 pymavlink.mav 모의 송신 객체."""

    def __init__(self) -> None:
        self.sent_command_longs = []
        self.sent_set_modes = []

    def command_long_send(
        self,
        target_system: int,
        target_component: int,
        command: int,
        confirmation: int,
        param1: float,
        param2: float,
        param3: float,
        param4: float,
        param5: float,
        param6: float,
        param7: float,
    ) -> None:
        self.sent_command_longs.append(
            {
                "target_system": target_system,
                "target_component": target_component,
                "command": command,
                "confirmation": confirmation,
                "param1": param1,
                "param2": param2,
                "param7": param7,
            }
        )

    def set_mode_send(self, target_system: int, base_mode: int, custom_mode: int) -> None:
        self.sent_set_modes.append(
            {
                "target_system": target_system,
                "base_mode": base_mode,
                "custom_mode": custom_mode,
            }
        )


class MockMAVConnection:
    """테스트용 MAVLink 연결 객체."""

    def __init__(self) -> None:
        self.mav = MockMAVProtocol()
        self.target_system = 1
        self.target_component = 1

    def mode_mapping(self) -> dict:
        return {"LOITER": 5, "RTL": 6, "LAND": 9}


def test_1_flight_command_service_has_set_connection_and_transmits_packet():
    """소켓 주입 후 TAKEOFF 명령 송출 시 MAVLink 바이너리 패킷이 실제 소켓으로 송출되는지 검증."""
    service = FlightCommandService()
    assert hasattr(service, "set_connection"), "FlightCommandService에 set_connection 메서드가 장착되어야 합니다."

    mock_conn = MockMAVConnection()
    service.set_connection(mock_conn)

    cmd = DroneCommandIn(
        command="TAKEOFF",
        drone_id="DRONE-01",
        param1=15.0,
    )
    result = service.dispatch_command(cmd)

    assert result["sent"] is True
    assert len(mock_conn.mav.sent_command_longs) >= 1
    takeoff_pkts = [p for p in mock_conn.mav.sent_command_longs if p["command"] == 22]
    assert len(takeoff_pkts) == 1
    sent_pkt = takeoff_pkts[0]
    assert sent_pkt["target_system"] == 1
    assert sent_pkt["param7"] == 15.0  # 이륙 고도


def test_2_flight_command_service_targets_drone_sysid_dynamically():
    """다중 기체 환경에서 DRONE-02 지정 시 target_system=2로 정확히 타겟팅되어 송출되는지 검증."""
    service = FlightCommandService()
    mock_conn = MockMAVConnection()
    service.set_connection(mock_conn)

    cmd = DroneCommandIn(
        command="ARM",
        drone_id="DRONE-02",
        param1=1.0,
    )
    service.dispatch_command(cmd)

    assert len(mock_conn.mav.sent_command_longs) == 1
    sent_pkt = mock_conn.mav.sent_command_longs[0]
    assert sent_pkt["target_system"] == 2  # DRONE-02 -> SysID 2


def test_3_global_service_singleton_supports_connection_injection_and_reset():
    """전역 싱글톤 get_flight_command_service()에 커넥션 주입 및 회수(자원 정리)가 안전하게 동작하는지 검증."""
    service = get_flight_command_service()
    mock_conn = MockMAVConnection()

    service.set_connection(mock_conn)
    assert service._connection is mock_conn

    service.set_connection(None)
    assert service._connection is None
