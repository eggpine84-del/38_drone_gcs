# -*- coding: utf-8 -*-
# [파일명]: test_pin_failsafe_workflow.py (복합 페일세이프 단계별 워크플로우 선행 핀-테스트)
# [원칙] 1. 3초 이상 통신 두절(LOST) 감지 | 2. EMERGENCY_RTH 강제 전환 | 3. 멱등 원장 보존
import pytest
from fastapi.testclient import TestClient
from main import app
from src.engine.core.drone_state_machine import DroneStatus
from src.engine.core.failsafe_evaluator import (
    FailsafeEvaluation,
    evaluate_heartbeat_timeout,
)
from src.engine.shell.drone_failsafe_service import DroneFailsafeService
from src.engine.shell.drone_repository import InMemoryDroneLedgerRepository


def test_pin_core_heartbeat_timeout_evaluator():
    """Core 순수 함수: 3초 초과 통신 두절 시 LOST 및 EMERGENCY_RTH 판정 (Full-Assertion)."""
    # 1. 정상 통신 (2.5초 경과)
    res_normal = evaluate_heartbeat_timeout(
        last_heartbeat_time=100.0,
        current_time=102.5,
        current_status=DroneStatus.IN_FLIGHT,
        timeout_seconds=3.0,
    )
    assert res_normal == FailsafeEvaluation(
        is_timeout=False,
        elapsed_seconds=2.5,
        next_status=DroneStatus.IN_FLIGHT,
        should_transition=False,
        alert_code="NORMAL",
    )

    # 2. 3.0초 초과 두절 (3.2초 경과) -> EMERGENCY_RTH 강제 전이
    res_timeout = evaluate_heartbeat_timeout(
        last_heartbeat_time=100.0,
        current_time=103.2,
        current_status=DroneStatus.IN_FLIGHT,
        timeout_seconds=3.0,
    )
    assert res_timeout == FailsafeEvaluation(
        is_timeout=True,
        elapsed_seconds=3.2,
        next_status=DroneStatus.EMERGENCY_RTH,
        should_transition=True,
        alert_code="LOST_HEARTBEAT_TIMEOUT",
    )


def test_pin_failsafe_service_idempotent_recording():
    """Service 멱등성: 통신 두절 감지 후 반복 호출 시 원장 중복 적재 0건 방어 (Full-Assertion)."""
    repo = InMemoryDroneLedgerRepository()
    service = DroneFailsafeService(repository=repo)

    # 1. 초기 하트비트 등록
    service.record_heartbeat("DRONE-01", timestamp=1000.0)

    # 2. 1차 비상 감찰 (1004.0초 -> 4초 경과, LOST 발생)
    res1 = service.check_drone_failsafe("DRONE-01", current_time=1004.0)
    assert res1.is_timeout is True
    assert res1.is_recorded is True
    assert res1.status == DroneStatus.EMERGENCY_RTH

    # 원장에 정확히 1건의 RTH 로그가 적재되었는지 확인
    logs = repo.list_by_drone("DRONE-01")
    assert len(logs) == 1
    assert logs[0].status == DroneStatus.EMERGENCY_RTH.value

    # 3. 2차 비상 감찰 (1005.0초 -> 여전히 두절 상태)
    # 이미 EMERGENCY_RTH 상태이므로 원장에 중복 적재되지 않아야 함 (멱등성)
    res2 = service.check_drone_failsafe("DRONE-01", current_time=1005.0)
    assert res2.is_timeout is True
    assert res2.is_recorded is False  # 중복 적재 0건 차단

    logs_after = repo.list_by_drone("DRONE-01")
    assert len(logs_after) == 1, "중복 원장 적재 발생 (멱등성 위반)"


def test_pin_failsafe_http_routes():
    """HTTP 엔드포인트: 하트비트 핑 및 비상 점검 B1 단일 봉투 통신 계약 검증."""
    client = TestClient(app)

    # 1. 하트비트 핑 전송 (POST /api/heartbeat)
    hb_payload = {
        "drone_id": "DRONE-02",
        "timestamp": 2000.0,
    }
    resp = client.post("/api/heartbeat", json=hb_payload)
    assert resp.status_code == 200
    hb_data = resp.json()
    assert hb_data["success"] is True
    assert hb_data["data"]["drone_id"] == "DRONE-02"

    # 2. 비상 감찰 실행 (POST /api/failsafe/check)
    check_payload = {
        "drone_id": "DRONE-02",
        "current_time": 2004.0,  # 4초 경과
    }
    resp_check = client.post("/api/failsafe/check", json=check_payload)
    assert resp_check.status_code == 200
    check_data = resp_check.json()
    assert check_data["success"] is True
    assert check_data["data"]["is_lost"] is True
    assert check_data["data"]["status"] == "EMERGENCY_RTH"
