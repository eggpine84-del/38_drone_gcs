"""
[Pin-Test First] 4_status_workflow 핀테스트 선작성
"""
import pytest
from docs.boilerplates.status_workflow.core import transition_order_status


def test_transition_order_status_valid():
    """접수 -> 승인 상태 전이가 정상 승인되어야 한다."""
    res = transition_order_status(current_status="RECEIVED", target_status="APPROVED", role="ADMIN")
    assert res["success"] is True
    assert res["data"]["status"] == "APPROVED"


def test_transition_order_status_invalid_backward():
    """완료 상태에서 접수 상태로 역주행 전이는 엄격히 거부되어야 한다."""
    res = transition_order_status(current_status="COMPLETED", target_status="RECEIVED", role="ADMIN")
    assert res["success"] is False
    assert res["error"] == "ERR_INVALID_TRANSITION"


def test_transition_order_status_unauthorized_role():
    """일반 직원은 취소 상태로 변경할 권한이 없어야 한다."""
    res = transition_order_status(current_status="RECEIVED", target_status="CANCELLED", role="STAFF")
    assert res["success"] is False
    assert res["error"] == "ERR_PERMISSION_DENIED"
