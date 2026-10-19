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
