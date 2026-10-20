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


def test_pin_flight_command_no_violations():
    """flight_command_service에 중첩 if 및 except: pass 에러 삼키기가 없음을 검증합니다."""
    import ast
    with open("src/features/dashboard/shell/flight_command_service.py", "r", encoding="utf-8") as f:
        tree = ast.parse(f.read())
    violations = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for sub in ast.walk(node):
                if isinstance(sub, ast.If):
                    if any(isinstance(c, ast.If) for stmt in sub.body for c in ast.walk(stmt)):
                        violations.append(f"중첩 if: {node.name} L{sub.lineno}")
                elif isinstance(sub, ast.ExceptHandler):
                    if len(sub.body) == 1 and isinstance(sub.body[0], (ast.Pass, ast.Constant)):
                        violations.append(f"에러 삼키기: {node.name} L{sub.lineno}")
    assert not violations, f"flight_command_service 위반 발견: {violations}"

