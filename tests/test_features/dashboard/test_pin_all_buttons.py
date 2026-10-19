# -*- coding: utf-8 -*-
"""관제탑 5대 핵심 액션바 및 15종 전술 서랍 버튼 전수 1:1 검증 핀-테스트."""
from fastapi.testclient import TestClient
import pytest

from main import app

# 관제 대시보드(dashboard.html)에 선언된 24개 전 버튼 정의 목록
ALL_DASHBOARD_BUTTONS = [
    # --- [상시 노출 5대 핵심 골든 액션 바] ---
    {"name": "메인 시동 (Arm)", "data": {"drone_id": "DRONE-01", "command": "ARM", "param1": "1.0"}},
    {"name": "메인 10m 이륙 (Takeoff)", "data": {"drone_id": "DRONE-01", "command": "TAKEOFF", "param1": "10.0"}},
    {"name": "메인 공중 정지 (Hold)", "data": {"drone_id": "DRONE-01", "command": "HOLD"}},
    {"name": "메인 원점 복귀 (RTL)", "data": {"drone_id": "DRONE-01", "command": "RTL"}},
    {"name": "메인 현위치 착륙 (Land)", "data": {"drone_id": "DRONE-01", "command": "LAND"}},

    # --- [전술 서랍: 1. 조그 패드] ---
    {"name": "서랍 조그 전진 (▲ 2m)", "data": {"drone_id": "DRONE-01", "command": "MOVE", "param1": "2.0"}},
    {"name": "서랍 조그 좌이동 (◀ 2m)", "data": {"drone_id": "DRONE-01", "command": "MOVE", "param2": "-2.0"}},
    {"name": "서랍 조그 정지", "data": {"drone_id": "DRONE-01", "command": "HOLD"}},
    {"name": "서랍 조그 우이동 (2m ▶)", "data": {"drone_id": "DRONE-01", "command": "MOVE", "param2": "2.0"}},
    {"name": "서랍 조그 후진 (▼ 2m)", "data": {"drone_id": "DRONE-01", "command": "MOVE", "param1": "-2.0"}},
    {"name": "서랍 조그 상승 (+1m)", "data": {"drone_id": "DRONE-01", "command": "MOVE", "param3": "-1.0"}},
    {"name": "서랍 조그 하강 (-1m)", "data": {"drone_id": "DRONE-01", "command": "MOVE", "param3": "1.0"}},

    # --- [전술 서랍: 2. 카메라 & 짐벌] ---
    {"name": "서랍 짐벌 수직 하향 (-90°)", "data": {"drone_id": "DRONE-01", "command": "GIMBAL", "param1": "-90.0"}},
    {"name": "서랍 짐벌 수평 정면 (0°)", "data": {"drone_id": "DRONE-01", "command": "GIMBAL", "param1": "0.0"}},
    {"name": "서랍 짐벌 사진 촬영 (Shutter)", "data": {"drone_id": "DRONE-01", "command": "GIMBAL", "param1": "1.0"}},
    {"name": "서랍 짐벌 동영상 녹화", "data": {"drone_id": "DRONE-01", "command": "GIMBAL", "param1": "2.0"}},

    # --- [전술 서랍: 3. 비행 모드 전환] ---
    {"name": "서랍 모드 LOITER", "data": {"drone_id": "DRONE-01", "command": "HOLD"}},
    {"name": "서랍 모드 GUIDED", "data": {"drone_id": "DRONE-01", "command": "GUIDED"}},
    {"name": "서랍 모드 LAND", "data": {"drone_id": "DRONE-01", "command": "LAND"}},
    {"name": "서랍 모드 RTL", "data": {"drone_id": "DRONE-01", "command": "RTL"}},
    {"name": "서랍 모드 AUTO", "data": {"drone_id": "DRONE-01", "command": "SET_MODE", "param1": "1.0"}},
    {"name": "서랍 모드 CIRCLE", "data": {"drone_id": "DRONE-01", "command": "SET_MODE", "param1": "7.0"}},

    # --- [전술 서랍: 4. 특수 임무 & 비상] ---
    {"name": "서랍 물품 투하 (Drop)", "data": {"drone_id": "DRONE-01", "command": "DROP"}},
    {"name": "서랍 긴급 모터 차단 (Kill)", "data": {"drone_id": "DRONE-01", "command": "KILL"}},
]


@pytest.mark.parametrize("btn", ALL_DASHBOARD_BUTTONS, ids=[b["name"] for b in ALL_DASHBOARD_BUTTONS])
def test_pin_all_dashboard_buttons(btn):
    """관제탑 메인 액션바 및 전술 서랍의 모든 버튼이 HTMX 폼 전송 시 400 에러 없이 200 OK로 송출되는지 전수 검증."""
    client = TestClient(app)

    # 브라우저 메타데이터가 일부 섞여 들어오는 실제 환경 시뮬레이션
    payload = {
        **btn["data"],
        "hx_current_url": "http://127.0.0.1:8000/",
    }

    response = client.post(
        "/api/features/dashboard/command",
        data=payload,
        headers={"HX-Request": "true"},
    )

    # 1. HTTP 200 OK 상태 코드 검증
    assert response.status_code == 200, f"[{btn['name']}] 요청 실패: status={response.status_code}, body={response.text}"

    # 2. HTMX 정상 피드백 HTML 렌더링 검증
    cmd_code = btn["data"]["command"]
    assert cmd_code in response.text, f"[{btn['name']}] 피드백 텍스트에 명령 코드 누락: {response.text}"
    assert "송출 성공" in response.text, f"[{btn['name']}] 송출 성공 피드백 누락: {response.text}"
