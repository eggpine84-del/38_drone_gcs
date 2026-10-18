"""
[Core] CRUD 비즈니스 검증 및 상태 전이 순수 함수
- 외부 I/O (DB/네트워크/시간/랜덤) 절대 금지
- 100% 결정론적 연산
"""
from typing import Dict, Any, Optional, TypedDict


class ItemPayload(TypedDict, total=False):
    item_id: str
    name: str
    category: str
    status: str
    is_deleted: bool


class ResultEnvelope(TypedDict):
    success: bool
    data: Optional[Dict[str, Any]]
    error: Optional[str]


def validate_item_input(name: Optional[str], category: Optional[str]) -> ResultEnvelope:
    """새 항목 생성/수정 시 입력값 유효성을 검증한다 (Guard Clause 적용)."""
    if not name or not name.strip():
        return {"success": False, "data": None, "error": "ERR_EMPTY_NAME"}

    clean_name = name.strip()
    if len(clean_name) < 2:
        return {"success": False, "data": None, "error": "ERR_NAME_TOO_SHORT"}

    clean_category = (category.strip() if category else "GENERAL") or "GENERAL"

    return {
        "success": True,
        "data": {
            "name": clean_name,
            "category": clean_category,
            "status": "ACTIVE",
            "is_deleted": False,
        },
        "error": None,
    }


def apply_soft_delete(item: Dict[str, Any]) -> ResultEnvelope:
    """원장 보호 원칙에 따라 항목을 논리 삭제(Soft Delete) 상태로 전이한다."""
    if not item:
        return {"success": False, "data": None, "error": "ERR_ITEM_NOT_FOUND"}

    updated = dict(item)
    updated["is_deleted"] = True
    updated["status"] = "ARCHIVED"
    return {"success": True, "data": updated, "error": None}
