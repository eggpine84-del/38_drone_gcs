# -*- coding: utf-8 -*-
# [파일명]: test_pin_mission_routes.py
# [목적]: 미션 및 명령 제어 엔드포인트 B1 단일 봉투 통신 계약 선행 핀-테스트
import pytest
from fastapi.testclient import TestClient
from main import app


@pytest.fixture
def client():
    """FastAPI 테스트 클라이언트 픽스처."""
    return TestClient(app)


def test_pin_mission_command_success_and_ledger(client: TestClient):
    """정상 시동 명령(ARM) 하달 시 200 OK 및 원장 상태 전이 기록 검증 (B1 봉투)."""
    # 1. 초기 텔레메트리 등록 (IDLE 상태)
    client.post(
        "/api/telemetry",
        json={
            "drone_id": "DRONE-CMD-01",
            "latitude": 37.5665,
            "longitude": 126.9780,
            "altitude": 0.0,
            "speed": 0.0,
            "battery": 90,
            "target_status": "IDLE",
            "timestamp": "2026-10-18T14:00:00Z",
        },
    )

    # 2. ARM 시동 명령 하달
    response = client.post(
        "/api/features/mission/command",
        json={
            "drone_id": "DRONE-CMD-01",
            "command": "ARM",
        },
    )
    assert response.status_code == 200
    res_json = response.json()
    assert res_json["success"] is True
    assert res_json["data"]["drone_id"] == "DRONE-CMD-01"
    assert res_json["data"]["next_status"] == "ARMED"
    assert res_json["error"] is None


def test_pin_mission_command_rejected_violating_precondition(client: TestClient):
    """금기 1항: 선행 상태 위반(IDLE 드론에 이륙 명령) 시 400 거부 검증."""
    client.post(
        "/api/telemetry",
        json={
            "drone_id": "DRONE-CMD-02",
            "latitude": 37.5665,
            "longitude": 126.9780,
            "altitude": 0.0,
            "speed": 0.0,
            "battery": 90,
            "target_status": "IDLE",
            "timestamp": "2026-10-18T14:00:00Z",
        },
    )

    response = client.post(
        "/api/features/mission/command",
        json={
            "drone_id": "DRONE-CMD-02",
            "command": "TAKEOFF",  # 시동 전 이륙 불가
        },
    )
    assert response.status_code == 400
    res_json = response.json()
    assert res_json["success"] is False
    assert res_json["data"] is None
    assert "시동(ARMED)" in res_json["error"]["message"]


def test_pin_mission_progress_calculation(client: TestClient):
    """현재 위치 기반 웨이포인트 진행률 계산 API 검증."""
    payload = {
        "drone_id": "DRONE-CMD-03",
        "current_latitude": 37.5665,
        "current_longitude": 126.9780,
        "current_altitude": 30.0,
        "current_waypoint_index": 0,
        "waypoints": [
            {"latitude": 37.5665, "longitude": 126.9780, "altitude": 30.0},
            {"latitude": 37.5675, "longitude": 126.9780, "altitude": 40.0},
        ],
    }
    response = client.post("/api/features/mission/progress", json=payload)
    assert response.status_code == 200
    res_json = response.json()
    assert res_json["success"] is True
    # 0번 인덱스 도착했으므로 다음 인덱스 1 전진 및 50% 진행률
    assert res_json["data"]["current_index"] == 1
    assert res_json["data"]["progress_pct"] == 50


def test_pin_mission_service_uses_explicit_constants_when_no_latest():
    """미션 서비스가 인라인 매직넘버 대신 명시적 기본 상수를 사용하는지 검증 (Red)."""
    from src.features.mission.shell import mission_service

    assert getattr(mission_service, "DEFAULT_MISSION_LATITUDE", None) == 37.5665
    assert getattr(mission_service, "DEFAULT_MISSION_LONGITUDE", None) == 126.9780
    assert getattr(mission_service, "DEFAULT_MISSION_BATTERY_PERCENT", None) == 100

