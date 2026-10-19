# -*- coding: utf-8 -*-
"""HTMX 폼 인코딩 비행 명령 송출 400 방어 재현 핀-테스트."""
from fastapi.testclient import TestClient
import pytest

from main import app


def test_pin_flight_command_form_urlencoded_success():
    """HTMX가 application/x-www-form-urlencoded 로 보낼 때 400 Bad Request 없이 200 정상 처리되는지 검증."""
    client = TestClient(app)

    # HTMX 메타 필드가 포함된 요청 시뮬레이션
    form_data = {
        "drone_id": "DRONE-01",
        "command": "ARM",
        "param1": "1.0",
        "hx_current_url": "http://127.0.0.1:8000/",
        "browser_cache_bust": "98765",
    }
    response = client.post(
        "/api/features/dashboard/command",
        data=form_data,
        headers={"HX-Request": "true"},
    )

    # 400 Bad Request가 발생하지 않고 200 OK와 함께 피드백 HTML이 반환되어야 함
    assert response.status_code == 200
    assert "ARM" in response.text

