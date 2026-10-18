# [파일명]: red_cache_core.py | [용도] 핀-테스트 Red 검증 세션 캐시 순수 코어 (Pure Functional Core)
import os
import json
import hashlib
from typing import Any, Dict


def calculate_test_hash(content: str) -> str:
    """테스트 코드 내용의 SHA-256 해시를 결정론적으로 계산하는 순수 함수."""
    if not content:
        return ""
    return hashlib.sha256(content.encode("utf-8", errors="replace")).hexdigest()


def is_red_cache_hit(
    cache_store: Dict[str, Any],
    test_rel_path: str,
    current_mtime: float,
    current_hash: str
) -> bool:
    """테스트 파일의 mtime과 내용 해시가 캐시 레코드와 100% 일치하는지 판정하는 순수 함수."""
    norm_path = test_rel_path.replace("\\", "/")
    record = cache_store.get(norm_path)
    if not isinstance(record, dict):
        return False

    is_verified = bool(record.get("verified", False))
    mtime_match = (record.get("mtime") == current_mtime)
    hash_match = (record.get("hash") == current_hash)
    return is_verified and mtime_match and hash_match


def create_red_cache_record(
    test_rel_path: str,
    current_mtime: float,
    current_hash: str
) -> Dict[str, Any]:
    """검증 완료된 핀-테스트의 신규 캐시 레코드를 생성하는 순수 함수."""
    return {
        "mtime": current_mtime,
        "hash": current_hash,
        "verified": True
    }


def load_red_cache(cache_file_path: str) -> Dict[str, Any]:
    """세션 캐시 파일을 안전하게 로드하는 I/O 함수 (손상/부재 시 빈 딕셔너리 안전 폴백)."""
    if not cache_file_path or not os.path.exists(cache_file_path):
        return {}
    try:
        with open(cache_file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_red_cache(cache_file_path: str, cache_data: Dict[str, Any]) -> None:
    """세션 캐시 데이터를 파일에 원자적으로 저장하는 I/O 함수."""
    if not cache_file_path:
        return
    try:
        dir_name = os.path.dirname(cache_file_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
        with open(cache_file_path, "w", encoding="utf-8") as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def clear_red_cache(cache_file_path: str) -> None:
    """세션 종료(Green 통과) 시 캐시 파일을 안전하게 소거하는 I/O 함수."""
    if cache_file_path and os.path.exists(cache_file_path):
        try:
            os.remove(cache_file_path)
        except Exception:
            pass


def check_red_status_with_cache(
    project_root: str,
    test_changes: list,
    verifier_fn: Any,
    cache_file_path: str = ""
) -> tuple:
    """캐시 적중 시 0초 통과, 미적중 시 실제 Red 검증 후 캐시에 등록하는 통합 헬퍼 함수."""
    if not cache_file_path:
        cache_file_path = os.path.join(project_root, ".agents", ".red_verified_cache.json")

    cache_store = load_red_cache(cache_file_path)

    # 1. mtime 역순 정렬 (최신 수정된 테스트 우선)
    sorted_tests = sorted(
        test_changes,
        key=lambda f: os.path.getmtime(os.path.join(project_root, f)) if os.path.exists(os.path.join(project_root, f)) else 0,
        reverse=True
    )

    # 2. 캐시 적중 여부 우선 순회 (0초 고속 패스)
    for t in sorted_tests:
        full_p = os.path.join(project_root, t)
        if not os.path.exists(full_p):
            continue
        try:
            mtime = os.path.getmtime(full_p)
            with open(full_p, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            h = calculate_test_hash(content)
            if is_red_cache_hit(cache_store, t, mtime, h):
                return True, t, ""
        except Exception:
            continue

    # 3. 캐시 미적중 시: 실제 verifier_fn을 통한 Red 실패 검증
    from core.pre_tool.pre_tool_guard_core import evaluate_multi_test_red_status
    has_red, verified_test, reject_reason = evaluate_multi_test_red_status(
        sorted_tests,
        verifier_fn=verifier_fn
    )

    # 4. 검증 성공 시 캐시에 안전 저장
    if has_red and verified_test:
        full_p = os.path.join(project_root, verified_test)
        if os.path.exists(full_p):
            try:
                mtime = os.path.getmtime(full_p)
                with open(full_p, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                h = calculate_test_hash(content)
                norm_key = verified_test.replace("\\", "/")
                cache_store[norm_key] = create_red_cache_record(norm_key, mtime, h)
                save_red_cache(cache_file_path, cache_store)
            except Exception:
                pass

    return has_red, verified_test, reject_reason

