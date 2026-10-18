"""
[Pin-Test First] 8_rate_limiter 핀테스트 선작성
"""
import pytest
from docs.boilerplates.feature_blocks.rate_limiter.core import check_rate_limit


def test_rate_limit_allowed_under_limit():
    """한도 내의 요청은 정상 허용되고 잔여량이 차감되어야 한다."""
    now = 1000.0
    history = [980.0, 990.0]  # 최근 2건
    res = check_rate_limit(
        client_key="client_ip_127.0.0.1",
        current_time=now,
        request_history=history,
        max_requests=5,
        window_seconds=60.0,
    )
    assert res["success"] is True
    assert res["data"]["allowed"] is True
    assert res["data"]["remaining"] == 2  # 5 - (2 + 1) = 2
    assert len(res["data"]["updated_history"]) == 3


def test_rate_limit_exceeded_blocked():
    """한도를 초과한 요청은 차단되고 429 안내 정보가 반환되어야 한다."""
    now = 1000.0
    history = [950.0, 960.0, 970.0, 980.0, 990.0]  # 이미 5건 꽉 참
    res = check_rate_limit(
        client_key="client_ip_127.0.0.1",
        current_time=now,
        request_history=history,
        max_requests=5,
        window_seconds=60.0,
    )
    assert res["success"] is False
    assert res["error"] == "ERR_RATE_LIMIT_EXCEEDED"
    assert res["data"]["allowed"] is False
    assert res["data"]["retry_after_seconds"] > 0
