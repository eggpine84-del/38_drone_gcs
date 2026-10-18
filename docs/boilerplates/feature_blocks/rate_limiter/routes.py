"""
[Shell] API 속도 제한 미들웨어 및 테스트 엔드포인트 (FastAPI)
"""
import time
from typing import Dict, List
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from docs.boilerplates.feature_blocks.rate_limiter.core import check_rate_limit

router = APIRouter(prefix="/sample-rate-limit", tags=["sample-rate-limit"])

# 인메모리 요청 이력 저장소 (IP/ClientKey -> List[float])
REQUEST_HISTORIES: Dict[str, List[float]] = {}


@router.get("/ping")
async def ping_endpoint(request: Request):
    """속도 제한 테스트 엔드포인트 Shell."""
    client_ip = request.client.host if request.client else "unknown_ip"
    now = time.time()
    history = REQUEST_HISTORIES.get(client_ip, [])

    # 분당 최대 10회 제한 테스트 규격
    res = check_rate_limit(
        client_key=client_ip,
        current_time=now,
        request_history=history,
        max_requests=10,
        window_seconds=60.0,
    )

    if not res["success"]:
        return JSONResponse(
            status_code=429,
            content={
                "success": False,
                "error": res["error"],
                "retry_after_seconds": res["data"]["retry_after_seconds"],
            },
        )

    REQUEST_HISTORIES[client_ip] = res["data"]["updated_history"]
    return JSONResponse(
        status_code=200,
        content={"success": True, "remaining": res["data"]["remaining"]},
    )
