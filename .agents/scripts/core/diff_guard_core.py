# [파일명]: diff_guard_core.py | [용도] 4대 작업 유형별 Git Diff 무결성 및 데이터 유실 판정 순수 코어 (Pure Functional Core)
import re
from typing import Any

DEFAULT_POLICY: dict[str, Any] = {
    "max_consecutive_deletions_in_feat": 15,
    "max_consecutive_deletions_in_change": 15,
    "max_consecutive_deletions_in_fix": 70,
    "protected_key_patterns": ["id", "key", "name", "code"],
    "banned_comment_patterns": ["기존 코드 동일", "기존코드동일", "unchanged", "TODO", "구현 예정", "..."],
    "bypass_dirs": [".agents", "docs", "templates"]
}


def _extract_identifiers(line: str, key_patterns: list[str]) -> list[str]:
    """라인 내에서 보호 대상 식별자 키(id, key, name, code)를 추출하는 순수 함수."""
    found = []
    lower = line.lower()
    for pat in key_patterns:
        regex = rf'["\']?{re.escape(pat)}["\']?\s*[:=]'
        if re.search(regex, lower):
            found.append(pat)
    return found


def _is_comment_line(line: str) -> bool:
    """순수 주석 라인인지 판별하는 순수 함수."""
    stripped = line.strip()
    return stripped.startswith(("#", "//", "/*", "*", "<!--"))


def _extract_string_literals(line: str) -> set[str]:
    """라인 내에서 따옴표/백틱 문자열 리터럴을 추출하는 순수 함수 (주석 제외)."""
    if _is_comment_line(line):
        return set()
    literals = set()
    pattern = r'''(?<!\\)(?:'([^'\\]*(?:\\.[^'\\]*)*)'|"([^"\\]*(?:\\.[^"\\]*)*)"|`([^`\\]*(?:\\.[^`\\]*)*)`)'''
    matches = re.findall(pattern, line)
    for m in matches:
        val = m[0] or m[1] or m[2]
        if val.strip():
            literals.add(val)
    return literals


def analyze_git_diff(
    diff_text: str,
    work_mode: str = "default",
    policy: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Git Diff 텍스트를 분석하여 4대 작업 유형별 위반 및 데이터 유실 여부를 결정론적으로 판정하는 순수 함수."""
    if not diff_text or not diff_text.strip():
        return {"decision": "allow", "violations": [], "reason": ""}

    cfg = dict(DEFAULT_POLICY)
    if policy:
        cfg.update(policy)

    mode = (work_mode or "default").lower().strip()
    violations: list[str] = []


    current_file = ""
    deleted_identifiers: list[str] = []
    added_identifiers: list[str] = []
    file_deleted_strings: dict[str, set[str]] = {}
    file_added_strings: dict[str, set[str]] = {}
    consecutive_deletions = 0
    max_consecutive_deletions = 0

    lines = diff_text.splitlines()
    for line in lines:
        if line.startswith("diff --git "):
            consecutive_deletions = 0
            b_idx = line.rfind("b/")
            if b_idx != -1:
                current_file = line[b_idx + 2:].strip('"\' ')
            else:
                parts = line.split()
                if len(parts) >= 4:
                    current_file = parts[3].strip('"').lstrip("b/").strip('"')
            continue

        if line.startswith("---") or line.startswith("+++") or line.startswith("@@"):
            consecutive_deletions = 0
            continue

        if line.startswith("+"):
            consecutive_deletions = 0
            added_content = line[1:].strip()

            bypass_dirs = cfg.get("bypass_dirs", [".agents", "docs", "templates"])
            is_config_or_doc = any(
                current_file.startswith(d.strip("/\\") + "/") or current_file == d.strip("/\\")
                for d in bypass_dirs
            )
            if not is_config_or_doc:
                scrubbed_line = re.sub(r"(['\"]).*?\1", "", added_content)
                scrubbed_line = re.sub(r"\[.*?\]", "", scrubbed_line)
                for banned in cfg["banned_comment_patterns"]:
                    if banned == "...":
                        if "..." in scrubbed_line or scrubbed_line.strip() == "...":
                            violations.append(f"게으른 축약 주석 감지 ('{banned}') at {current_file}")
                            break
                    else:
                        if banned in added_content:
                            violations.append(f"게으른 축약 주석 감지 ('{banned}') at {current_file}")
                            break

                added_identifiers.extend(_extract_identifiers(added_content, cfg["protected_key_patterns"]))
                if mode == "refactor":
                    file_added_strings.setdefault(current_file, set()).update(_extract_string_literals(added_content))
            continue

        if line.startswith("-"):
            consecutive_deletions += 1
            if consecutive_deletions > max_consecutive_deletions:
                max_consecutive_deletions = consecutive_deletions

            deleted_content = line[1:].strip()
            bypass_dirs = cfg.get("bypass_dirs", [".agents", "docs", "templates"])
            is_config_or_doc = any(
                current_file.startswith(d.strip("/\\") + "/") or current_file == d.strip("/\\")
                for d in bypass_dirs
            )
            if not is_config_or_doc:
                deleted_identifiers.extend(_extract_identifiers(deleted_content, cfg["protected_key_patterns"]))
                if mode == "refactor":
                    file_deleted_strings.setdefault(current_file, set()).update(_extract_string_literals(deleted_content))
            continue

        consecutive_deletions = 0

    if mode == "refactor":
        if any(line.startswith("diff --git") and (" a/tests/" in line or " b/tests/" in line) for line in lines):
            violations.append("리팩토링(refactor) 모드 중 테스트 코드 변조 감지 (tests/ 수정 금지)")

        for fname, del_set in file_deleted_strings.items():
            add_set = file_added_strings.get(fname, set())
            lost = del_set - add_set
            if lost:
                sample = sorted(list(lost))[:3]
                violations.append(f"리팩토링(refactor) 모드 중 문자열 리터럴 변조 감지 (소실/변조: {sample}) at {fname}")

    if mode in ("feat", "change", "fix"):
        if policy and f"max_consecutive_deletions_in_{mode}" in policy:
            limit = policy[f"max_consecutive_deletions_in_{mode}"]
        elif mode in ("feat", "fix"):
            limit = cfg.get("max_consecutive_deletions_in_feat", 15)
        else:
            limit = None

        if limit is not None and max_consecutive_deletions >= limit:
            mode_names = {"feat": "기능 추가(feat)", "change": "기능 변경(change)", "fix": "버그 수리(fix)"}
            mode_kr = mode_names.get(mode, mode)
            violations.append(f"{mode_kr} 모드 중 기존 로직 대량 삭제 감지 ({max_consecutive_deletions}줄 연속 삭제, 한도 {limit}줄)")

    if len(deleted_identifiers) > len(added_identifiers):
        net_loss = len(deleted_identifiers) - len(added_identifiers)
        violations.append(f"핵심 데이터/식별자 순감소 누락 감지 (삭제 {len(deleted_identifiers)}개 > 추가 {len(added_identifiers)}개, 순손실 {net_loss}개)")

    if violations:
        reason = " | ".join(violations)
        return {"decision": "block", "violations": violations, "reason": reason}

    return {"decision": "allow", "violations": [], "reason": ""}
