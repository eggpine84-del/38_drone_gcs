"""
[Shell] 외부 Webhook 수신 엔드포인트 (FastAPI)
"""
import os
from fastapi import APIRouter, Request, Header
from fastapi.responses import JSONResponse
from docs.boilerplates.feature_blocks.webhook_receiver.core import verify_webhook_signature, process_idempotent_event

router = APIRouter(prefix="/sample-webhook", tags=["sample-webhook"])

# 멱등성 보장을 위한 처리된 이벤트 인메모리 저장소 (실무에서는 Redis/DB 전담)
PROCESSED_EVENT_IDS = set()
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "default_sample_secret_key")


@router.post("/receiver")
async def webhook_endpoint(request: Request, x_signature: str = Header(default="")):
    """외부 웹훅 서명 검증 및 멱등 처리 Shell."""
    body_bytes = await request.body()

    # 1. 서명 검증
    sig_res = verify_webhook_signature(
        payload_bytes=body_bytes,
        signature_header=x_signature,
        secret_key=WEBHOOK_SECRET,
    )
    if not sig_res["success"]:
        return JSONResponse(status_code=401, content={"success": False, "error": sig_res["error"]})

    # 2. 페이로드 파싱 및 멱등성 검사
    payload = await request.json()
    event_id = payload.get("id", "")

    idemp_res = process_idempotent_event(event_id=event_id, processed_ids=PROCESSED_EVENT_IDS)
    if not idemp_res["success"]:
        return JSONResponse(status_code=409, content={"success": False, "error": idemp_res["error"]})

    PROCESSED_EVENT_IDS.add(event_id)
    return JSONResponse(status_code=200, content={"success": True, "event_id": event_id})
