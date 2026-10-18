"""
[Core] 감사 로그 / 히스토리 Diff 순수 연산 함수
"""
from typing import Dict, Any, List, TypedDict


class DiffEntry(TypedDict):
    field: str
    old_val: Any
    new_val: Any


def extract_audit_diff(before: Dict[str, Any], after: Dict[str, Any]) -> List[DiffEntry]:
    """두 딕셔너리를 비교하여 변경된 필드들의 차이점(Diff)을 순수 추출한다."""
    diffs: List[DiffEntry] = []
    all_keys = set(before.keys()).union(set(after.keys()))

    for key in sorted(all_keys):
        # 내부 관리용 키 제외 예시
        if key in ("updated_at", "created_at"):
            continue

        old_v = before.get(key)
        new_v = after.get(key)

        if old_v != new_v:
            diffs.append({
                "field": key,
                "old_val": old_v,
                "new_val": new_v,
            })

    return diffs
