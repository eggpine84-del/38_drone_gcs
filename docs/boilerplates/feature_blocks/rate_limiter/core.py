"""
[Core] 슬라이딩 윈도우 기반 API 속도 제한 순수 판정 모듈 (FCIS Pure Core)
"""
from typing import Dict, Any, TypedDict, Optional, List


class RateLimitResult(TypedDict):
    success: bool
    data: Optional[Dict[str, Any]]
    error: Optional[str]


def check_rate_limit(
    client_key: str,
    current_time: float,
    request_history: List[float],
    max_requests: int = 60,
    window_seconds: float = 60.0,
) -> RateLimitResult:
    """슬라이딩 윈도우 방식으로 요청 허용 여부 및 잔여량을 순수 계산한다."""
    if not client_key:
        return {"success": False, "data": None, "error": "ERR_INVALID_CLIENT_KEY"}
    if max_requests <= 0 or window_seconds <= 0:
        return {"success": False, "data": None, "error": "ERR_INVALID_CONFIG"}

    # 1. 윈도우 범위 밖의 만료된 타임스탬프 필터링
    threshold = current_time - window_seconds
    valid_history = [t for t in request_history if t > threshold]

    # 2. 한도 초과 판정
    if len(valid_history) >= max_requests:
        oldest_valid = valid_history[0]
        retry_after = max(0.0, round(oldest_valid + window_seconds - current_time, 2))
        return {
            "success": False,
            "data": {
                "allowed": False,
                "remaining": 0,
                "retry_after_seconds": retry_after,
                "updated_history": valid_history,
            },
            "error": "ERR_RATE_LIMIT_EXCEEDED",
        }

    # 3. 요청 허용 및 새 타임스탬프 추가
    updated_history = valid_history + [current_time]
    remaining = max_requests - len(updated_history)

    return {
        "success": True,
        "data": {
            "allowed": True,
            "remaining": remaining,
            "retry_after_seconds": 0.0,
            "updated_history": updated_history,
        },
        "error": None,
    }
