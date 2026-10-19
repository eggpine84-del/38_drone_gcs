# -*- coding: utf-8 -*-
"""동적 기체 자동 감지 및 관제 화면 실시간 바인딩 핀-테스트 (Pin Test Dynamic Drone Binding).

FCIS 및 Pin-Test First 원칙:
1. Pure Core: resolve_active_drone_id() 존재 및 순수 결정론적 선출 검증 (빈값, 다중 기체, 폴백).
2. Dashboard Routes: 템플릿 렌더링 시 active_drone_id가 올바르게 주입되는지 검증.
3. UI Markup: 대시보드 관제 기체 표시 및 버튼(hx-vals)에 동적 active_drone_id가 적용되는지 검증.
"""
from starlette.testclient import TestClient
import pytest
from fastapi import FastAPI

import src.engine.core.mavlink_parser_core as core_mod
from src.features.dashboard.shell.dashboard_routes import router


def test_pin_resolve_active_drone_id_pure_core():
    """순수 코어 함수 resolve_active_drone_id의 결정론적 활성 기체 선출 검증."""
    # 0. 함수 존재 단언 (미구현 시 명확한 비즈니스 AssertionError 유발)
    assert hasattr(core_mod, "resolve_active_drone_id"), "resolve_active_drone_id 순수 코어 함수가 구현되어야 합니다."
    resolve_fn = getattr(core_mod, "resolve_active_drone_id")

    # 1. 등록 기체가 1대일 때 해당 기체 즉시 선출
    assert resolve_fn(["DRONE-01"], "DEFAULT") == "DRONE-01"

    # 2. 다중 기체일 때 첫 번째(또는 최신) 기체 선출
    assert resolve_fn(["DRONE-02", "DRONE-01"], "DEFAULT") == "DRONE-02"

    # 3. 등록 기체가 없을 때 안전 폴백 반환
    assert resolve_fn([], "FALLBACK-1") == "FALLBACK-1"
    assert resolve_fn([], "") == "DRONE-01"

    # 4. None/비정상 입력 가드
    assert resolve_fn(None, "SAFE-1") == "SAFE-1"


def test_pin_dashboard_renders_active_drone_id_dynamically(monkeypatch):
    """대시보드 라우터가 저장소의 실제 활성 기체 ID를 화면 및 액션 버튼에 동적 렌더링하는지 검증."""
    from src.engine.core.telemetry_record import TelemetryRecord
    from src.engine.core.drone_state_machine import DroneStatus
    import src.features.dashboard.shell.dashboard_routes as d_routes

    # 1. get_all_active_drones_latest() 모킹하여 DRONE-01 기체 레코드 주입
    mock_record = {
        "id": 1,
        "drone_id": "DRONE-01",
        "latitude": 37.5665,
        "longitude": 126.9780,
        "altitude": 15.0,
        "speed": 4.5,
        "battery": 92,
        "status": "IN_FLIGHT",
        "timestamp": "2026-10-19T12:00:00Z",
    }
    monkeypatch.setattr(d_routes, "get_all_active_drones_latest", lambda: [mock_record])

    app = FastAPI()
    app.include_router(router)

    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200

    html = response.text
    # 2. 화면 상단 관제 기체 배지에 감지된 DRONE-01이 동적으로 표시되는지 검증
    assert "DRONE-01" in html, "화면에 감지된 활성 기체 ID(DRONE-01)가 표시되어야 합니다."

    # 3. 5대 액션바 버튼에 하드코딩 대신 DRONE-01이 바인딩되는지 검증
    assert '{"drone_id": "DRONE-01", "command": "ARM", "param1": 1.0}' in html, "시동 버튼에 동적 drone_id가 바인딩되어야 합니다."
    assert '{"drone_id": "DRONE-01", "command": "TAKEOFF", "param1": 10.0}' in html, "이륙 버튼에 동적 drone_id가 바인딩되어야 합니다."
