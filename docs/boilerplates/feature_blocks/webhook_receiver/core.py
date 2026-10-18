"""
[Core] 외부 Webhook HMAC 서명 검증 및 멱등성 판정 순수 함수 (FCIS Pure Core)
"""
import hmac
import hashlib
from typing import Dict, Any, TypedDict, Optional, Set


class WebhookResult(TypedDict):
    success: bool
    data: Optional[Dict[str, Any]]
    error: Optional[str]


def verify_webhook_signature(
    payload_bytes: bytes,
    signature_header: str,
    secret_key: str,
) -> WebhookResult:
    """HMAC-SHA256 서명 일치 여부를 타이밍 공격 없이 안전하게 검증한다."""
    if not payload_bytes:
        return {"success": False, "data": None, "error": "ERR_EMPTY_PAYLOAD"}
    if not signature_header:
        return {"success": False, "data": None, "error": "ERR_MISSING_SIGNATURE"}
    if not secret_key:
        return {"success": False, "data": None, "error": "ERR_MISSING_SECRET"}

    # 서명 계산 및 타이밍 공격 방지 안전 비교
    computed_sig = hmac.new(
        secret_key.encode("utf-8"),
        payload_bytes,
        hashlib.sha256,
    ).hexdigest()

    # 접두사(예: sha256=) 처리 지원
    cleaned_header = signature_header.replace("sha256=", "").strip()
    if not hmac.compare_digest(computed_sig, cleaned_header):
        return {"success": False, "data": None, "error": "ERR_INVALID_SIGNATURE"}

    return {"success": True, "data": {"verified": True}, "error": None}


def process_idempotent_event(
    event_id: str,
    processed_ids: Set[str],
) -> WebhookResult:
    """이벤트 ID(멱등키) 중복 처리 여부를 판정한다."""
    cleaned_id = event_id.strip() if event_id else ""
    if not cleaned_id:
        return {"success": False, "data": None, "error": "ERR_INVALID_EVENT_ID"}

    if cleaned_id in processed_ids:
        return {"success": False, "data": None, "error": "ERR_DUPLICATE_EVENT"}

    return {"success": True, "data": {"event_id": cleaned_id, "can_process": True}, "error": None}
