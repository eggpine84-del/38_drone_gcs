# -*- coding: utf-8 -*-
"""동적 mode_mapping 기반 GUIDED 권한 전환 및 연쇄 이륙 파이프라인 핀-테스트 (Pin-Test).

1. TAKEOFF 명령 시: SET_MODE(GUIDED) ➔ ARM(시동) ➔ TAKEOFF(이륙) 3단계 연쇄 송출 검증.
2. ARM 명령 시: SET_MODE(GUIDED) 선전환 후 안전 시동 송출 검증.
3. GUIDED 단독 명령 시: mode_mapping 기반 동적 GUIDED 모드 전환 패킷 송출 검증.
"""
import pytest
from src.features.dashboard.shell.command_dto import DroneCommandIn
from src.features.dashboard.shell.flight_command_service import FlightCommandService


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
    """테스트용 MAVLink 연결 객체 (동적 mode_mapping 제공)."""

    def __init__(self) -> None:
        self.mav = MockMAVProtocol()
        self.target_system = 1
        self.target_component = 1

    def mode_mapping(self) -> dict:
        # ArduCopter 표준 모드 매핑
        return {
            "STABILIZE": 0,
            "GUIDED": 4,
            "LOITER": 5,
            "RTL": 6,
            "LAND": 9,
        }


def test_1_takeoff_triggers_guided_arm_takeoff_pipeline():
    """TAKEOFF 명령 접수 시 GUIDED 모드 전환 ➔ 시동(ARM) ➔ 이륙 3단 연쇄 송출을 단언."""
    service = FlightCommandService()
    mock_conn = MockMAVConnection()
    service.set_connection(mock_conn)

    cmd = DroneCommandIn(command="TAKEOFF", drone_id="DRONE-01", param1=12.0)
    result = service.dispatch_command(cmd)

    assert result["sent"] is True

    # 1단계: GUIDED 모드 전환 단언 (custom_mode: 4)
    assert len(mock_conn.mav.sent_set_modes) >= 1
    assert mock_conn.mav.sent_set_modes[0]["custom_mode"] == 4

    # 2단계 & 3단계: ARM(시동) 및 TAKEOFF(이륙) 단언
    commands_sent = [p["command"] for p in mock_conn.mav.sent_command_longs]
    # MAV_CMD_COMPONENT_ARM_DISARM(400) 및 MAV_CMD_NAV_TAKEOFF(22) 순차 송출 단언
    assert 400 in commands_sent, "TAKEOFF 파이프라인에 시동(ARM) 선행 송출이 포함되어야 합니다."
    assert 22 in commands_sent, "TAKEOFF 파이프라인에 이륙(TAKEOFF) 송출이 포함되어야 합니다."

    # 이륙 명령 인자 확인 (param7 = 12.0m)
    takeoff_pkt = [p for p in mock_conn.mav.sent_command_longs if p["command"] == 22][0]
    assert takeoff_pkt["param7"] == 12.0


def test_2_arm_triggers_guided_mode_pre_transition():
    """ARM 명령 접수 시 ArduPilot 시동 거부 방지를 위해 GUIDED 모드 선전환 후 시동을 거는지 단언."""
    service = FlightCommandService()
    mock_conn = MockMAVConnection()
    service.set_connection(mock_conn)

    cmd = DroneCommandIn(command="ARM", drone_id="DRONE-01", param1=1.0)
    result = service.dispatch_command(cmd)

    assert result["sent"] is True
    # GUIDED 모드 선전환이 1회 이상 발생했는지 단언
    assert len(mock_conn.mav.sent_set_modes) >= 1
    assert mock_conn.mav.sent_set_modes[0]["custom_mode"] == 4

    # 시동 명령(400) 송출 단언
    assert len(mock_conn.mav.sent_command_longs) >= 1
    assert mock_conn.mav.sent_command_longs[0]["command"] == 400


def test_3_independent_guided_command_dispatches_correctly():
    """전술 서랍의 독립 GUIDED 모드 전환 명령이 정확한 custom_mode(4)로 발송되는지 단언."""
    service = FlightCommandService()
    mock_conn = MockMAVConnection()
    service.set_connection(mock_conn)

    cmd = DroneCommandIn(command="GUIDED", drone_id="DRONE-01")
    result = service.dispatch_command(cmd)

    assert result["sent"] is True
    assert len(mock_conn.mav.sent_set_modes) == 1
    assert mock_conn.mav.sent_set_modes[0]["custom_mode"] == 4
