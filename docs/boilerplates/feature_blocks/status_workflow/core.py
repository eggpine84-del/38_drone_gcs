"""
[Core] 상태 머신 및 전이 유효성 순수 검증 함수 (Table-Driven)
"""
from typing import Dict, Any, TypedDict, Optional, Set


class WorkflowResult(TypedDict):
    success: bool
    data: Optional[Dict[str, Any]]
    error: Optional[str]


# Table-Driven: 허용된 상태 전이 매핑 규격 (if-elif 금지)
ALLOWED_TRANSITIONS: Dict[str, Set[str]] = {
    "RECEIVED": {"APPROVED", "CANCELLED"},
    "APPROVED": {"PROCESSING", "CANCELLED"},
    "PROCESSING": {"COMPLETED"},
    "COMPLETED": set(),  # 최종 완료 시 전이 불가
    "CANCELLED": set(),  # 최종 취소 시 전이 불가
}


def transition_order_status(current_status: str, target_status: str, role: str) -> WorkflowResult:
    """주문/결재 상태 전이 유효성을 순수 검증한다."""
    curr = current_status.upper()
    target = target_status.upper()

    # 1. 권한 체크 (CANCELLED는 ADMIN만 가능)
    if target == "CANCELLED" and role != "ADMIN":
        return {"success": False, "data": None, "error": "ERR_PERMISSION_DENIED"}

    # 2. 상태 전이 테이블 검증
    allowed_targets = ALLOWED_TRANSITIONS.get(curr, set())
    if target not in allowed_targets:
        return {"success": False, "data": None, "error": "ERR_INVALID_TRANSITION"}

    return {
        "success": True,
        "data": {
            "previous_status": curr,
            "status": target,
        },
        "error": None,
    }
