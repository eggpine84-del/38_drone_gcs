"""
[Shell] 보안 4대 물리 게이트 FastAPI 단일 관문 미들웨어 (Imperative Shell)
모든 HTTP 요청의 입구에서 4대 게이트를 기계적으로 통타하여 위반 시 즉시 400/403/413/422로 반사한다.
"""
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import time
from docs.boilerplates.feature_blocks.security_guard.core import (
    check_gate1_injection,
    check_gate4_resource_ceiling,
    MAX_ALLOWED_PAYLOAD_BYTES
)

class SecurityGateMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # [Gate 4: 자원 고갈 차단 - 페이로드 크기 헤더 사전 검문]
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > MAX_ALLOWED_PAYLOAD_BYTES:
            return JSONResponse(
                status_code=413,
                content={
                    "success": False,
                    "error": "ERR_PAYLOAD_TOO_LARGE",
                    "message": "요청 페이로드 크기가 허용 상한선을 초과했습니다."
                }
            )

        # [Gate 1: 경계 붕괴 차단 - 쿼리 스트링 인젝션 감찰]
        query_str = str(request.query_params)
        gate1_res = check_gate1_injection(query_str)
        if not gate1_res["passed"]:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "error": gate1_res["error_code"],
                    "message": gate1_res["message"]
                }
            )

        # 본 처리 수행
        response: Response = await call_next(request)

        # [보안 헤더 강제 부착 - 브라우저 및 전송 보호]
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        # 처리 시간(ms) 기록
        process_time = (time.time() - start_time) * 1000
        response.headers["X-Response-Time-Ms"] = f"{process_time:.2f}"

        return response
