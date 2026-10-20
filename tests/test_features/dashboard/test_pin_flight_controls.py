# -*- coding: utf-8 -*-
"""웹 대시보드 비행 제어 및 전술 서랍 핀-테스트 (Flight Controls Pin-Test).

1. 상용 5대 비행 명령(ARM, TAKEOFF, HOLD, RTL, LAND) 및 수동 기동(MOVE) REST API 검증.
2. 메인 페이지 내 5대 핵심 액션바 및 15종 전술 서랍(Drawer) 마크업 렌더링 검증.
"""
import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_1_flight_command_api_success():
    """상용 5대 핵심 명령(ARM, TAKEOFF, HOLD, RTL, LAND)이 단일 봉투(B1)로 정상 송출되는지 검증."""
    commands = [
        {"drone_id": "SITL-COPTER-1", "command": "ARM", "param1": 1.0},
        {"drone_id": "SITL-COPTER-1", "command": "TAKEOFF", "param1": 10.0},
        {"drone_id": "SITL-COPTER-1", "command": "HOLD"},
        {"drone_id": "SITL-COPTER-1", "command": "RTL"},
        {"drone_id": "SITL-COPTER-1", "command": "LAND"},
        {"drone_id": "SITL-COPTER-1", "command": "MOVE", "param1": 2.0, "param2": 0.0, "param3": 0.0},
    ]

    for payload in commands:
        res = client.post("/api/features/dashboard/command", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert data["data"]["command"] == payload["command"]
        assert data["data"]["drone_id"] == "SITL-COPTER-1"
        assert data["error"] is None


def test_2_flight_command_api_validation_failure():
    """유효하지 않은 명령어나 빈 드론 ID 전송 시 400 또는 422 에러로 자동 차단되는지 검증."""
    # 1. 빈 드론 ID
    res1 = client.post("/api/features/dashboard/command", json={"drone_id": "", "command": "TAKEOFF"})
    assert res1.status_code in (400, 422)

    # 2. 지원하지 않는 이상한 명령어
    res2 = client.post("/api/features/dashboard/command", json={"drone_id": "DRONE-01", "command": "UNKNOWN_ACTION"})
    assert res2.status_code in (400, 422)


def test_3_dashboard_page_contains_dual_control_ui():
    """대시보드 HTML에 상시 노출 5대 액션바와 우측 전술 서랍(Drawer) 마크업이 포함되어 있는지 검증."""
    res = client.get("/")
    assert res.status_code == 200
    html = res.text

    # 1. 상시 5대 핵심 액션바 검증
    assert "main-flight-action-bar" in html
    assert "btn-action-arm" in html
    assert "btn-action-takeoff" in html
    assert "btn-action-hold" in html
    assert "btn-action-rtl" in html
    assert "btn-action-land" in html

    # 2. 우측 전술 서랍(Drawer) 검증
    assert "tactical-drawer-panel" in html
    assert "drawer-toggle-btn" in html
    assert "jog-pad-container" in html


def test_4_move_command_uses_body_offset_ned_frame():
    """MOVE 명령이 MAV_FRAME_BODY_OFFSET_NED 프레임 및 위치 마스크로 정밀 송출되는지 검증."""
    from unittest.mock import MagicMock
    from src.features.dashboard.shell.flight_command_service import FlightCommandService
    from src.features.dashboard.shell.command_dto import DroneCommandIn

    mock_conn = MagicMock()
    mock_conn.target_system = 1
    mock_conn.target_component = 1
    service = FlightCommandService(connection=mock_conn)

    # 상승 1m 명령 (z = -1.0)
    cmd = DroneCommandIn(drone_id="DRONE-01", command="MOVE", param1=0.0, param2=0.0, param3=-1.0)
    service.dispatch_command(cmd)

    calls = mock_conn.mav.set_position_target_local_ned_send.call_args_list
    assert len(calls) >= 1
    # call args: (time_boot_ms, target_system, target_component, coordinate_frame, type_mask, x, y, z, vx, vy, vz, afx, afy, afz, yaw, yaw_rate)
    args = calls[0].args
    # MAV_FRAME_BODY_OFFSET_NED (9)
    assert args[3] == 9, "좌표 프레임은 MAV_FRAME_BODY_OFFSET_NED(9)여야 합니다."
    # type_mask: 위치만 제어 (0b0000111111111000 = 0x0DF8 = 3576)
    assert args[4] == 0b0000111111111000, "타입 마스크는 위치 오프셋 전용(0b0000111111111000)이어야 합니다."
    assert args[7] == -1.0, "z 위치 오프셋이 -1.0m이어야 합니다."


def test_5_drop_command_dispatches_gripper_release():
    """DROP 명령이 MAV_CMD_DO_GRIPPER(211) 명령으로 MAVLink 송출되는지 검증."""
    from unittest.mock import MagicMock
    from src.features.dashboard.shell.flight_command_service import FlightCommandService
    from src.features.dashboard.shell.command_dto import DroneCommandIn

    mock_conn = MagicMock()
    mock_conn.target_system = 1
    mock_conn.target_component = 1
    service = FlightCommandService(connection=mock_conn)

    drop_cmd = DroneCommandIn(drone_id="DRONE-01", command="DROP")
    res = service.dispatch_command(drop_cmd)
    assert res["sent"] is True

    calls = mock_conn.mav.command_long_send.call_args_list
    assert len(calls) >= 1
    # call args: (target_system, target_component, command, confirmation, param1, param2, ...)
    args = calls[0].args
    assert args[2] == 211, "MAV_CMD_DO_GRIPPER(211)가 송출되어야 합니다."
    assert args[5] == 0, "그리퍼 방출(action=0)이어야 합니다."

