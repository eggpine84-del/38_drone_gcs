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


def test_pin_command_payload_flatten_compliance():
    """비행 명령 파싱 엔드포인트가 else 내부 중첩 if 없이 평탄화되었는지 검증."""
    import ast
    with open("src/features/dashboard/shell/dashboard_routes.py", "r", encoding="utf-8") as f:
        tree = ast.parse(f.read())
    violations = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for sub in ast.walk(node):
                if isinstance(sub, ast.If):
                    is_elif = sub.orelse and len(sub.orelse) == 1 and isinstance(sub.orelse[0], ast.If)
                    if not is_elif and sub.orelse:
                        for child in sub.orelse:
                            for n in ast.walk(child):
                                if isinstance(n, ast.If):
                                    violations.append(f"{node.name}: L{sub.lineno}")
    assert not violations, f"dashboard_routes else 내부 if 발견: {violations}"


