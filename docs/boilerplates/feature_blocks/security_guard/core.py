"""
[Core] 보안 4대 물리 게이트 순수 검증 엔진 (FCIS Pure Core)
외부 I/O, DB, 네트워크 호출이 일절 없는 100% 순수 함수로 구성된다.
"""
from typing import Dict, Any, TypedDict, Optional, Set, List
import re

class GateResult(TypedDict):
    passed: bool
    gate_name: str
    error_code: Optional[str]
    message: str

# 1. Gate 1: 경계 붕괴 (Injection) 감찰 패턴
_SQLI_PATTERNS = [
    re.compile(r"(\b(UNION(\s+ALL)?|SELECT|INSERT|UPDATE|DELETE|DROP|ALTER|EXEC)\b)", re.IGNORECASE),
    re.compile(r"(--|#|/\*|\*/|;)", re.IGNORECASE),
    re.compile(r"('|\"|%27|%22)", re.IGNORECASE),
]

def check_gate1_injection(raw_input: str) -> GateResult:
    """원시 입력값 내 SQL/명령어 인젝션 유발 메타문자를 순수 정규식으로 감찰한다."""
    if not raw_input:
        return {"passed": True, "gate_name": "Gate1_Injection", "error_code": None, "message": "OK"}
    
    for pattern in _SQLI_PATTERNS:
        if pattern.search(raw_input):
            return {
                "passed": False,
                "gate_name": "Gate1_Injection",
                "error_code": "ERR_INJECTION_DETECTED",
                "message": "입력값에 문법 경계를 붕괴시키는 위험 문자가 포함되어 있습니다."
            }
    return {"passed": True, "gate_name": "Gate1_Injection", "error_code": None, "message": "OK"}


# 2. Gate 2: 신뢰 왜곡 (Auth & BOLA/IDOR) 감찰
def check_gate2_ownership(resource_owner_id: str, requester_id: str, is_admin: bool = False) -> GateResult:
    """요청자 신원과 자원 소유권의 일치 여부를 순수 대조한다."""
    if is_admin:
        return {"passed": True, "gate_name": "Gate2_Ownership", "error_code": None, "message": "Admin bypass"}
    
    if not requester_id or not resource_owner_id:
        return {
            "passed": False,
            "gate_name": "Gate2_Ownership",
            "error_code": "ERR_IDENTITY_MISSING",
            "message": "인증 식별자 또는 자원 소유권 정보가 누락되었습니다."
        }
    
    if str(resource_owner_id) != str(requester_id):
        return {
            "passed": False,
            "gate_name": "Gate2_Ownership",
            "error_code": "ERR_BOLA_IDOR_VIOLATION",
            "message": "타인의 자원에 접근하거나 조작할 권한이 없습니다."
        }
    
    return {"passed": True, "gate_name": "Gate2_Ownership", "error_code": None, "message": "OK"}


# 3. Gate 3: 상태 교란 (Race Condition / TOCTOU) 감찰
def check_gate3_atomic_balance(current_balance: int, deduct_amount: int) -> GateResult:
    """원자적 조건 검사 (잔액 부족 및 음수 출금 시도 사전 차단)."""
    if deduct_amount <= 0:
        return {
            "passed": False,
            "gate_name": "Gate3_AtomicState",
            "error_code": "ERR_INVALID_AMOUNT",
            "message": "차감 금액은 0보다 커야 합니다."
        }
    
    if current_balance < deduct_amount:
        return {
            "passed": False,
            "gate_name": "Gate3_AtomicState",
            "error_code": "ERR_INSUFFICIENT_FUNDS",
            "message": "현재 잔액이 요청 금액보다 부족합니다."
        }
    
    return {"passed": True, "gate_name": "Gate3_AtomicState", "error_code": None, "message": "OK"}


# 4. Gate 4: 자원 고갈 (Resource Exhaustion / DoS) 감찰
MAX_ALLOWED_PAYLOAD_BYTES = 1024 * 1024  # 1MB 상한
MAX_ALLOWED_LIMIT = 100                 # 목록 조회 최대 상한

def check_gate4_resource_ceiling(payload_size_bytes: int, query_limit: Optional[int] = None) -> GateResult:
    """페이로드 크기 및 쿼리 상한선을 기계적으로 강제한다."""
    if payload_size_bytes > MAX_ALLOWED_PAYLOAD_BYTES:
        return {
            "passed": False,
            "gate_name": "Gate4_ResourceCeiling",
            "error_code": "ERR_PAYLOAD_TOO_LARGE",
            "message": f"요청 크기가 상한선({MAX_ALLOWED_PAYLOAD_BYTES} bytes)을 초과했습니다."
        }
    
    if query_limit is not None and query_limit > MAX_ALLOWED_LIMIT:
        return {
            "passed": False,
            "gate_name": "Gate4_ResourceCeiling",
            "error_code": "ERR_LIMIT_EXCEEDED",
            "message": f"조회 건수 상한선({MAX_ALLOWED_LIMIT})을 초과했습니다."
        }
        
    return {"passed": True, "gate_name": "Gate4_ResourceCeiling", "error_code": None, "message": "OK"}
