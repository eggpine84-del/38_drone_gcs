"""
[Pin-Test First] 5_audit_log 핀테스트 선작성
"""
import pytest
from docs.boilerplates.audit_log.core import extract_audit_diff


def test_extract_audit_diff_no_change():
    """동일 객체 비교 시 빈 diff 목록을 반환해야 한다."""
    before = {"name": "홍길동", "role": "USER"}
    after = {"name": "홍길동", "role": "USER"}
    diffs = extract_audit_diff(before, after)
    assert len(diffs) == 0


def test_extract_audit_diff_with_changes():
    """필드 수정 시 변경 전/후 값이 정확히 추적되어야 한다."""
    before = {"name": "홍길동", "role": "USER"}
    after = {"name": "홍길동", "role": "ADMIN"}
    diffs = extract_audit_diff(before, after)
    assert len(diffs) == 1
    assert diffs[0]["field"] == "role"
    assert diffs[0]["old_val"] == "USER"
    assert diffs[0]["new_val"] == "ADMIN"
