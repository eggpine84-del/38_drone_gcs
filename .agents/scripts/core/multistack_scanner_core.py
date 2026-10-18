# [파일명]: multistack_scanner_core.py | [용도] 다중 스택 소스/테스트 디렉터리 수집 및 라인 수 집계 순수 코어 (Pure Functional Core)
import os
import re
from typing import Dict, List, Optional, Set, Tuple

# 디렉터리 순회 시 즉각 제외할 블랙리스트 (Zero-Glitch & Fast Scan)
BANNED_SCAN_DIRS: Set[str] = {
    ".git",
    "node_modules",
    "dist",
    "build",
    ".next",
    "__pycache__",
    ".pytest_cache",
    ".venv",
    "venv",
    ".idea",
    ".vscode",
    "coverage",
    ".turbo",
}

# 라인 수 검사 대상 소스코드 확장자 화이트리스트
CODE_EXTENSIONS: Set[str] = {
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".go",
}


def collect_all_source_dirs(
    workspace_root: str,
    target_dir_names: Optional[List[str]] = None
) -> List[str]:
    """워크스페이스 내에서 지정된 이름(예: src)을 가진 모든 유효한 소스 디렉터리를 수집하는 순수 함수.

    외부 라이브러리(node_modules, dist 등)는 엄격히 배제됩니다.

    Args:
        workspace_root: 워크스페이스 루트 경로
        target_dir_names: 탐색할 디렉터리 명칭 목록 (기본값: ["src"])

    Returns:
        List[str]: 상대 경로 목록 (예: ["src", "remotion/src"])
    """
    target_names = set(target_dir_names or ["src"])
    found_dirs: List[str] = []
    norm_root = os.path.abspath(workspace_root)

    if not os.path.exists(norm_root):
        return found_dirs

    for root, dirs, _ in os.walk(norm_root):
        # 0.001초 만에 블랙리스트 디렉터리 가지치기 (Pruning)
        dirs[:] = [d for d in dirs if d not in BANNED_SCAN_DIRS and not d.startswith(".")]

        rel_dir = os.path.relpath(root, norm_root).replace("\\", "/")
        dir_base = os.path.basename(root)

        if dir_base in target_names:
            if rel_dir != ".":
                found_dirs.append(rel_dir)

    return sorted(found_dirs)


def collect_all_test_dirs(workspace_root: str) -> List[str]:
    """워크스페이스 내의 모든 유효한 테스트 디렉터리(tests, test, __tests__)를 수집하는 순수 함수."""
    test_dir_names = {"tests", "test", "__tests__"}
    found_dirs: List[str] = []
    norm_root = os.path.abspath(workspace_root)

    if not os.path.exists(norm_root):
        return found_dirs

    for root, dirs, _ in os.walk(norm_root):
        dirs[:] = [d for d in dirs if d not in BANNED_SCAN_DIRS and not d.startswith(".")]

        rel_dir = os.path.relpath(root, norm_root).replace("\\", "/")
        dir_base = os.path.basename(root)

        if dir_base in test_dir_names:
            if rel_dir != ".":
                found_dirs.append(rel_dir)

    return sorted(found_dirs)


def scan_multistack_line_counts(
    workspace_root: str,
    target_dirs: List[str],
    max_file_size_bytes: int = 1048576
) -> Dict[str, int]:
    """수집된 다중 디렉터리 내의 소스코드 파일별 라인 수를 0.01초 내에 전수 계산하는 순수 함수."""
    counts: Dict[str, int] = {}
    norm_root = os.path.abspath(workspace_root)

    for tdir in target_dirs:
        abs_tdir = os.path.join(norm_root, tdir)
        if not os.path.exists(abs_tdir):
            continue

        for root, dirs, files in os.walk(abs_tdir):
            dirs[:] = [d for d in dirs if d not in BANNED_SCAN_DIRS and not d.startswith(".")]

            for fname in files:
                _, ext = os.path.splitext(fname)
                if ext.lower() not in CODE_EXTENSIONS:
                    continue

                abs_file = os.path.join(root, fname)
                try:
                    # 1MB 초과 대용량 파일은 자동 스킵 (보안 및 성능 방어)
                    if os.path.getsize(abs_file) > max_file_size_bytes:
                        continue

                    with open(abs_file, "r", encoding="utf-8", errors="ignore") as f:
                        line_count = sum(1 for _ in f)

                    rel_path = os.path.relpath(abs_file, norm_root).replace("\\", "/")
                    counts[rel_path] = line_count
                except Exception:
                    continue

    return counts
    

def check_multistack_test_deletion(
    old_code: str,
    target_code: str,
    replacement_code: str,
    target_rel: str
) -> Tuple[bool, str]:
    """Python, TypeScript, Go 테스트 코드의 임의 삭제/약화 여부를 정규식으로 감찰하는 순수 함수."""
    py_deleted = set(re.findall(r"def\s+(test_\w+)\s*\(", target_code))
    py_preserved = set(re.findall(r"def\s+(test_\w+)\s*\(", replacement_code))
    missing_py = py_deleted - py_preserved

    ts_pattern = r"""(?:it|test)\s*\(\s*['"`]([^'"`]+)['"`]"""
    ts_deleted = set(re.findall(ts_pattern, target_code))
    ts_preserved = set(re.findall(ts_pattern, replacement_code))
    missing_ts = ts_deleted - ts_preserved

    go_pattern = r"func\s+(Test\w+)\s*\("
    go_deleted = set(re.findall(go_pattern, target_code))
    go_preserved = set(re.findall(go_pattern, replacement_code))
    missing_go = go_deleted - go_preserved

    missing_all = missing_py.union(missing_ts).union(missing_go)

    if not target_code and replacement_code:
        old_py = set(re.findall(r"def\s+(test_\w+)\s*\(", old_code))
        new_py = set(re.findall(r"def\s+(test_\w+)\s*\(", replacement_code))
        if len(new_py) < len(old_py):
            missing_all.update(old_py - new_py)

        old_ts = set(re.findall(ts_pattern, old_code))
        new_ts = set(re.findall(ts_pattern, replacement_code))
        if len(new_ts) < len(old_ts):
            missing_all.update(old_ts - new_ts)

        old_go = set(re.findall(go_pattern, old_code))
        new_go = set(re.findall(go_pattern, replacement_code))
        if len(new_go) < len(old_go):
            missing_all.update(old_go - new_go)

    if missing_all:
        reason = (
            f"[테스트 게이트 차단: 테스트 케이스 임의 삭제/약화 금지]\n"
            f"수정 시도 중인 테스트 파일 '{target_rel}'에서 기존 테스트 케이스가 누락되었습니다: {sorted(list(missing_all))}\n"
            f"철칙: 기존 정상 테스트 코드는 영구 보존되어야 하며 삭제·변형·스킵이 절대 금지됩니다."
        )
        return False, reason

    return True, ""


def is_test_file_for_stack(rel_path: str, stack_type: str) -> bool:
    """대상 파일이 해당 언어 스택의 유효한 테스트 파일인지 판정하는 순수 함수."""
    norm = rel_path.replace("\\", "/").lower()
    base = os.path.basename(norm)

    if stack_type == "python":
        return norm.endswith(".py") and ("tests/" in norm or norm.startswith("test/") or base.startswith("test_") or base.endswith("_test.py"))

    if stack_type in ["typescript", "javascript"]:
        is_ts_ext = norm.endswith((".ts", ".tsx", ".js", ".jsx"))
        is_test_pattern = (
            base.endswith((".test.ts", ".test.tsx", ".spec.ts", ".spec.tsx", ".test.js", ".spec.js"))
            or "tests/" in norm
            or "/test/" in norm
            or norm.startswith("test/")
            or norm.startswith("tests/")
        )
        return is_ts_ext and is_test_pattern

    if stack_type == "go":
        return norm.endswith("_test.go")

    return False


