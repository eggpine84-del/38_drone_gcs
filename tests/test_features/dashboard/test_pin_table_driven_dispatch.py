# -*- coding: utf-8 -*-
"""비행 명령 서비스 Table-Driven Dispatch 아키텍처 핀-테스트."""
import pytest
from src.features.dashboard.shell.flight_command_service import FlightCommandService
from src.features.dashboard.shell.command_dto import DroneCommandIn


def test_flight_command_service_table_driven_dispatch():
    """FlightCommandService가 Table-Driven Dispatch 매핑 테이블을 보유하고 10종 명령을 올바르게 매핑하는지 검증합니다."""
    service = FlightCommandService()

    # 1. 아키텍처 규격: _COMMAND_DISPATCH_TABLE 무순서 딕셔너리 존재 확인
    assert hasattr(service, "_COMMAND_DISPATCH_TABLE"), "FlightCommandService에 _COMMAND_DISPATCH_TABLE이 정의되어야 합니다."
    table = service._COMMAND_DISPATCH_TABLE
    assert isinstance(table, dict), "_COMMAND_DISPATCH_TABLE은 dict 타입이어야 합니다."

    # 2. 필수 10종 명령 핸들러 매핑 확인
    required_commands = [
        "ARM", "DISARM", "TAKEOFF", "GUIDED", "HOLD", "LOITER",
        "RTL", "LAND", "MOVE", "GIMBAL", "KILL"
    ]
    for cmd_code in required_commands:
        assert cmd_code in table, f"{cmd_code} 명령이 _COMMAND_DISPATCH_TABLE에 매핑되어 있어야 합니다."
        assert callable(table[cmd_code]), f"{cmd_code} 핸들러는 호출 가능한 함수/메서드여야 합니다."

    # 3. dispatch_command 실행 규격 검증
    cmd = DroneCommandIn(command="ARM", drone_id="DRONE-01", param1=1.0)
    res = service.dispatch_command(cmd)
    assert res["sent"] is True
    assert res["command"] == "ARM"
