# -*- coding: utf-8 -*-
# [파일명]: test_pin_geofence_routes.py
# [목적]: 지오펜스 감찰 API 및 B1 단일 봉투 / B2 extra='forbid' DTO 통신 계약 선행 핀-테스트
import pytest
from fastapi.testclient import TestClient
from main import app


@pytest.fixture
def client():
    """FastAPI 테스트 클라이언트 픽스처."""
    return TestClient(app)


def test_pin_geofence_check_safe_flight(client: TestClient):
    """정상 비행 구역 내 좌표 전송 시 200 OK 및 is_breached=False 검증 (B1 봉투)."""
    payload = {
        "drone_id": "DRONE-GEO-01",
        "latitude": 37.5650,
        "longitude": 126.9750,
        "allowed_polygon": [
            [37.5600, 126.9700],
            [37.5700, 126.9700],
            [37.5700, 126.9850],
            [37.5600, 126.9850],
        ],
        "nfz_list": [],
    }
    response = client.post("/api/features/geofence/check", json=payload)
    assert response.status_code == 200
    res_json = response.json()
    assert res_json["success"] is True
    assert res_json["data"]["drone_id"] == "DRONE-GEO-01"
    assert res_json["data"]["is_breached"] is False
    assert res_json["data"]["recommended_status"] == "IN_FLIGHT"
    assert res_json["error"] is None


def test_pin_geofence_check_breach_forces_rth(client: TestClient):
    """지오펜스 이탈 또는 NFZ 침범 시 EMERGENCY_RTH 반환 및 원장 영구 적재 검증."""
    payload = {
        "drone_id": "DRONE-GEO-ALERT",
        "latitude": 37.5866,  # NFZ 좌표
        "longitude": 126.9748,
        "allowed_polygon": [],
        "nfz_list": [
            {
                "name": "청와대 NFZ",
                "latitude": 37.5866,
                "longitude": 126.9748,
                "radius_meters": 500.0,
            }
        ],
    }
    response = client.post("/api/features/geofence/check", json=payload)
    assert response.status_code == 200
    res_json = response.json()
    assert res_json["success"] is True
    assert res_json["data"]["is_breached"] is True
    assert res_json["data"]["breach_type"] == "NFZ_INTRUSION"
    assert res_json["data"]["recommended_status"] == "EMERGENCY_RTH"


def test_pin_geofence_dto_extra_fields_forbidden(client: TestClient):
    """B2 헌법: 허가되지 않은 필드(hack_flag 등) 인입 시 422 또는 400 자동 거부 검증."""
    payload = {
        "drone_id": "DRONE-GEO-02",
        "latitude": 37.5650,
        "longitude": 126.9750,
        "hack_flag": "malicious_injection",  # 허용되지 않은 필드
    }
    response = client.post("/api/features/geofence/check", json=payload)
    assert response.status_code in (400, 422)


def test_pin_geofence_breach_records_failsafe_zero_battery():
    """침범 감지 시 사전 원장 이력이 없는 드론은 50% 날조 없이 0% 비상 기본값으로 기록되는지 검증 (Red)."""
    from src.features.geofence.shell.geofence_service import GeofenceService
    from src.features.geofence.shell.geofence_dto import GeofenceCheckRequest
    from src.engine.shell.drone_repository import InMemoryDroneLedgerRepository

    repo = InMemoryDroneLedgerRepository()
    service = GeofenceService(repository=repo)

    req = GeofenceCheckRequest(
        drone_id="DRONE-NEW-BREACH",
        latitude=37.5866,
        longitude=126.9748,
        allowed_polygon=[],
        nfz_list=[{"name": "NFZ", "latitude": 37.5866, "longitude": 126.9748, "radius_meters": 500.0}],
    )
    res = service.check_and_enforce(req)
    assert res["is_breached"] is True

    record = repo.get_latest("DRONE-NEW-BREACH")
    assert record is not None
    # 50% 날조 없이 정확히 0% 기록 검증
    assert record.battery == 0

