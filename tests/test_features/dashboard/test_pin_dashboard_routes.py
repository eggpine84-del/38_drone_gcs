# -*- coding: utf-8 -*-
# [파일명]: test_pin_dashboard_routes.py
# [목적]: 관제 대시보드 엔드포인트 및 HTMX 부분 조각 통신 계약 핀-테스트
import pytest
from fastapi.testclient import TestClient
from main import app


@pytest.fixture
def client():
    """FastAPI 테스트 클라이언트 픽스처."""
    return TestClient(app)


def test_pin_dashboard_main_page(client: TestClient):
    """메인 관제 대시보드 GET / 요청 시 200 OK 및 레이아웃이 정상 렌더링되는지 검증."""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    content = response.text
    assert "<!DOCTYPE html>" in content
    assert "GCS" in content or "관제" in content


def test_pin_dashboard_htmx_stream_fragment(client: TestClient):
    """HTMX 요청(HX-Request: true) 시 전체 페이지가 아닌 순수 HTML 조각(Fragment)을 반환하는지 검증."""
    response = client.get(
        "/api/features/dashboard/stream",
        headers={"HX-Request": "true"}
    )
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    content = response.text
    # 헌법: HTMX 부분 조각에는 <!DOCTYPE, <html, <body 가 포함되지 않아야 함
    assert "<!DOCTYPE" not in content
    assert "<html" not in content
    assert "<body" not in content


def test_pin_dashboard_renders_active_drones(client: TestClient):
    """텔레메트리가 등록되었을 때 관제 대시보드 스트림에 드론 ID가 정상 렌더링되는지 검증."""
    # 1. 테스트 드론 텔레메트리 1건 전송
    client.post(
        "/api/telemetry",
        json={
            "drone_id": "DRONE-ALPHA",
            "latitude": 37.5665,
            "longitude": 126.9780,
            "altitude": 0.0,
            "speed": 0.0,
            "battery": 88,
            "target_status": "ARMED",
            "timestamp": "2026-10-18T14:00:00Z",
        },
    )

    # 2. 대시보드 스트림 조회
    response = client.get(
        "/api/features/dashboard/stream",
        headers={"HX-Request": "true"}
    )
    assert response.status_code == 200
    assert "DRONE-ALPHA" in response.text
    assert "88%" in response.text or "88" in response.text
