# -*- coding: utf-8 -*-
"""대시보드 하트비트 윈도우 기반 활성 기체 필터링 및 MAVLink FCU 시동 규격 재현 핀-테스트."""
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock
import pytest

from src.engine.shell.db_adapter import execute_command
from src.engine.shell.db_schema import init_db
from src.features.dashboard.core.dashboard_core import compute_dashboard_summary
from src.features.dashboard.shell.command_dto import DroneCommandIn
from src.features.dashboard.shell.dashboard_repository import get_all_active_drones_latest
from src.features.dashboard.shell.flight_command_service import FlightCommandService


def test_active_drone_heartbeat_window_filters_ghost_drone(tmp_path):
    """오래 전 전원이 꺼진 유령 기체(SITL-COPTER-1)가 하트비트 윈도우 밖으로 밀려나 자동 페이드아웃되는지 검증."""
    db_file = str(tmp_path / "test_gcs.db")
    init_db(db_file)

    now = datetime.now(timezone.utc)
    recent_time = (now - timedelta(seconds=2)).isoformat()
    ghost_time = (now - timedelta(seconds=7200)).isoformat()

    # 1. 2시간 전 전원 꺼진 유령 기체 비상 상태 삽입
    insert_sql = (
        "INSERT INTO telemetry_logs "
        "(drone_id, latitude, longitude, altitude, speed, battery, status, timestamp) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?);"
    )
    execute_command(
        insert_sql,
        ("SITL-COPTER-1", 37.123, 127.123, 0.0, 0.0, 0, "EMERGENCY_RTH", ghost_time),
        db_path=db_file,
    )

    # 2. 2초 전 현재 정상 비행 중인 활성 기체 삽입
    execute_command(
        insert_sql,
        ("DRONE-01", 37.456, 127.456, 15.0, 5.0, 90, "IN_FLIGHT", recent_time),
        db_path=db_file,
    )

    # 3. 하트비트 윈도우 10초 적용하여 조회
    active_records = get_all_active_drones_latest(db_path=db_file, max_age_seconds=10.0)

    # [Full Assertion]
    assert len(active_records) == 1
    assert active_records[0]["drone_id"] == "DRONE-01"
    assert active_records[0]["status"] == "IN_FLIGHT"

    # 관제 요약 집계 시 비상 경보가 거짓(False)으로 즉시 정상화되어야 함
    summary = compute_dashboard_summary(active_records)
    assert summary["has_emergency"] is False
    assert summary["emergency_count"] == 0
    assert summary["total_drones"] == 1


def test_flight_command_service_targets_autopilot_component():
    """ArduPilot FCU 시동 및 이륙 시 MAV_COMP_ID_AUTOPILOT1(1) 컴포넌트로 정확히 송출되는지 검증."""
    mock_conn = MagicMock()
    mock_conn.target_system = 1
    mock_conn.target_component = 1
    mock_conn.mode_mapping.return_value = {"GUIDED": 4}

    svc = FlightCommandService(connection=mock_conn)

    # 1. ARM 시동 테스트
    arm_cmd = DroneCommandIn(command="ARM", drone_id="DRONE-01", param1=1.0)
    res = svc.dispatch_command(arm_cmd)

    assert res["sent"] is True
    # command_long_send 호출 인자 중 target_component가 1이어야 함
    calls = mock_conn.mav.command_long_send.call_args_list
    assert len(calls) >= 1
    # call signature: target_sys, target_comp, command, ...
    args = calls[0].args
    assert args[0] == 1  # target_system (DRONE-01 -> 1)
    assert args[1] == 1  # target_component (MAV_COMP_ID_AUTOPILOT1)


def test_pin_dashboard_repository_no_error_swallowing():
    """dashboard_repository 모듈에 except: pass 에러 삼키기가 없음을 검증합니다."""
    import ast
    with open("src/features/dashboard/shell/dashboard_repository.py", "r", encoding="utf-8") as f:
        tree = ast.parse(f.read())
    swallowed = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler):
            if len(node.body) == 1 and isinstance(node.body[0], (ast.Pass, ast.Constant)):
                swallowed.append(f"L{node.lineno}")
    assert not swallowed, f"dashboard_repository 에러 삼키기 발견: {swallowed}"


def test_pin_is_within_window_bidirectional_guard():
    """_is_within_window가 5초 초과 미래 시각 및 비정형 타임스탬프를 거부(False)하는지 검증합니다."""
    from src.features.dashboard.shell.dashboard_repository import _is_within_window
    now = datetime.now(timezone.utc)

    # 1. 정상 과거 10초 전 -> True
    recent = (now - timedelta(seconds=10)).isoformat()
    assert _is_within_window(recent, 60.0) is True

    # 2. 70초 전 과거 -> False
    past = (now - timedelta(seconds=70)).isoformat()
    assert _is_within_window(past, 60.0) is False

    # 3. 1초 미래 (정상 클럭 오차) -> True
    slight_future = (now + timedelta(seconds=1)).isoformat()
    assert _is_within_window(slight_future, 60.0) is True

    # 4. 10초 초과 미래 시각 왜곡 패킷 -> False (Red 목표: 기존에는 음수 diff로 True 반환함)
    far_future = (now + timedelta(seconds=100)).isoformat()
    assert _is_within_window(far_future, 60.0) is False

    # 5. 비정형 포맷 문자열 ('1005.0') -> False (Red 목표: 기존에는 Exception 시 True 반환함)
    assert _is_within_window("1005.0", 60.0) is False


