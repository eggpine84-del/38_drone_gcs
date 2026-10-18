# -*- coding: utf-8 -*-
# [파일명]: test_pin_telemetry_routes.py (단발 텔레메트리 엔드포인트 선행 핀-테스트)
# [원칙] 1. B1 단일 봉투 규격 | 2. B2 extra='forbid' DTO 살균 | 3. Full-Assertion
import pytest
from fastapi.testclient import TestClient
from main import app


@pytest.fixture
def client():
    """FastAPI 테스트 클라이언트 픽스처."""
    return TestClient(app)


def test_pin_telemetry_endpoint_success(client):
    """정상 수신: B1 단일 봉투 규격 및 200 OK 검증 (Full-Assertion)."""
    payload = {
        "drone_id": "DRONE-01",
        "latitude": 37.5665,
        "longitude": 126.9780,
        "altitude": 0.0,
        "speed": 0.0,
        "battery": 95,
        "target_status": "ARMED",
        "timestamp": "2026-10-18T14:00:00Z",
    }
    response = client.post("/api/telemetry", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert data["error"] is None
    assert data["data"]["drone_id"] == "DRONE-01"
    assert data["data"]["status"] == "ARMED"
    assert data["data"]["is_failsafe_forced"] is False
    assert "record_id" in data["data"]


def test_pin_telemetry_endpoint_extra_forbid(client):
    """B2 규격: 미정의 키 주입 시 422 거부 검증 (화이트리스트 강제)."""
    payload = {
        "drone_id": "DRONE-01",
        "latitude": 37.5665,
        "longitude": 126.9780,
        "altitude": 0.0,
        "speed": 0.0,
        "battery": 95,
        "target_status": "ARMED",
        "timestamp": "2026-10-18T14:00:00Z",
        "hacked_admin_override": True,  # 미정의 키
    }
    response = client.post("/api/telemetry", json=payload)
    assert response.status_code == 422


def test_pin_telemetry_endpoint_missing_required_field(client):
    """B2 규격: 필수 필드 누락 시 422 Fail-Fast 차단 검증."""
    payload = {
        "drone_id": "DRONE-01",
        # latitude 누락
        "longitude": 126.9780,
        "altitude": 0.0,
        "speed": 0.0,
        "battery": 95,
        "target_status": "ARMED",
        "timestamp": "2026-10-18T14:00:00Z",
    }
    response = client.post("/api/telemetry", json=payload)
    assert response.status_code == 422


def test_pin_telemetry_endpoint_business_violation_400(client):
    """비즈니스 헌법 위반: 고도 음수 등 이상 수치 유입 시 400 및 B1 에러 봉투 검증."""
    payload = {
        "drone_id": "DRONE-01",
        "latitude": 37.5665,
        "longitude": 126.9780,
        "altitude": -25.0,  # 불가 음수 고도
        "speed": 0.0,
        "battery": 95,
        "target_status": "ARMED",
        "timestamp": "2026-10-18T14:00:00Z",
    }
    response = client.post("/api/telemetry", json=payload)
    assert response.status_code == 400

    data = response.json()
    assert data["success"] is False
    assert data["data"] is None
    assert data["error"]["code"] == "TRANSITION_REJECTED"
    assert "INVALID_SENSOR_INVARIANT" in data["error"]["message"]
    assert "ALTITUDE_NEGATIVE" in data["error"]["violations"]
