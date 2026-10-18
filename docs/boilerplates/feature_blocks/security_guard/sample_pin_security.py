"""
[Pin-Test First] 10_security_guard 4대 물리 게이트 전수 핀테스트
"""
import pytest
from docs.boilerplates.feature_blocks.security_guard.core import (
    check_gate1_injection,
    check_gate2_ownership,
    check_gate3_atomic_balance,
    check_gate4_resource_ceiling,
)

# --- Gate 1: 경계 붕괴 (Injection) 핀테스트 ---

def test_gate1_normal_input_passed():
    """정상 문자열 입력은 통과해야 한다."""
    res = check_gate1_injection("user_search_keyword_123")
    assert res["passed"] is True
    assert res["error_code"] is None

def test_gate1_sql_injection_blocked():
    """SQL 인젝션 메타문자 포함 시 즉시 차단되어야 한다."""
    res = check_gate1_injection("admin' OR '1'='1")
    assert res["passed"] is False
    assert res["error_code"] == "ERR_INJECTION_DETECTED"

def test_gate1_union_select_blocked():
    """UNION SELECT 구문 삽입 시 즉시 차단되어야 한다."""
    res = check_gate1_injection("1 UNION SELECT * FROM users")
    assert res["passed"] is False
    assert res["error_code"] == "ERR_INJECTION_DETECTED"


# --- Gate 2: 신뢰 왜곡 (Auth & IDOR) 핀테스트 ---

def test_gate2_same_owner_passed():
    """자원 소유자와 요청자가 일치하면 통과해야 한다."""
    res = check_gate2_ownership(resource_owner_id="user_100", requester_id="user_100")
    assert res["passed"] is True
    assert res["error_code"] is None

def test_gate2_idor_different_owner_blocked():
    """타인의 자원에 접근 시 IDOR 위반으로 즉시 차단되어야 한다."""
    res = check_gate2_ownership(resource_owner_id="user_100", requester_id="attacker_999")
    assert res["passed"] is False
    assert res["error_code"] == "ERR_BOLA_IDOR_VIOLATION"

def test_gate2_admin_bypass():
    """관리자 권한일 경우 검증을 통과해야 한다."""
    res = check_gate2_ownership(resource_owner_id="user_100", requester_id="admin_001", is_admin=True)
    assert res["passed"] is True


# --- Gate 3: 상태 교란 (Race Condition / TOCTOU) 핀테스트 ---

def test_gate3_balance_deduct_sufficient():
    """잔액이 충분할 경우 차감 검증을 통과해야 한다."""
    res = check_gate3_atomic_balance(current_balance=50000, deduct_amount=10000)
    assert res["passed"] is True
    assert res["error_code"] is None

def test_gate3_balance_insufficient_blocked():
    """잔액보다 큰 금액 차감 시도 시 즉시 거부되어야 한다."""
    res = check_gate3_atomic_balance(current_balance=5000, deduct_amount=10000)
    assert res["passed"] is False
    assert res["error_code"] == "ERR_INSUFFICIENT_FUNDS"

def test_gate3_negative_amount_blocked():
    """0원 이하의 음수 금액 차감 시도는 즉시 거부되어야 한다."""
    res = check_gate3_atomic_balance(current_balance=50000, deduct_amount=-500)
    assert res["passed"] is False
    assert res["error_code"] == "ERR_INVALID_AMOUNT"


# --- Gate 4: 자원 고갈 (Resource Ceiling) 핀테스트 ---

def test_gate4_within_limit_passed():
    """제한 범위 내 페이로드 및 쿼리 한도는 통과해야 한다."""
    res = check_gate4_resource_ceiling(payload_size_bytes=5000, query_limit=50)
    assert res["passed"] is True
    assert res["error_code"] is None

def test_gate4_payload_too_large_blocked():
    """1MB 초과 페이로드는 자원 고갈 위험으로 즉시 차단되어야 한다."""
    huge_bytes = 2 * 1024 * 1024
    res = check_gate4_resource_ceiling(payload_size_bytes=huge_bytes)
    assert res["passed"] is False
    assert res["error_code"] == "ERR_PAYLOAD_TOO_LARGE"

def test_gate4_query_limit_exceeded_blocked():
    """목록 조회 한도(100건) 초과 요청 시 즉시 차단되어야 한다."""
    res = check_gate4_resource_ceiling(payload_size_bytes=100, query_limit=500)
    assert res["passed"] is False
    assert res["error_code"] == "ERR_LIMIT_EXCEEDED"
