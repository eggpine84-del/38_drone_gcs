# [파일명]: tia_core.py | [용도] 3단계 계층형 테스트 아키텍처(TIA) 3대 언어 짝꿍 탐색 및 도메인 추출 순수 코어
import os
import re
from typing import List, Optional, Set, Tuple

DEFAULT_FALLBACK_PATTERNS: List[str] = [
    "shared/",
    "/shared/",
    "core/constants.py",
    "constants.py",
    "types/",
    "/types/",
    "guard_config.json",
    "hooks.json"
]

BYPASS_EXTENSIONS: Set[str] = {
    ".md", ".canvas", ".txt", ".png", ".jpg", ".jpeg", ".svg",
    ".ico", ".log", ".json", ".yaml", ".yml", ".toml"
}


def _normalize_path(path: str) -> str:
    """윈도우 및 POSIX 경로 구분자를 '/'로 단일화하고 공백을 제거하는 순수 함수."""
    if not path or not isinstance(path, str):
        return ""
    return path.replace("\\", "/").strip().strip('"'' ')


def _generate_python_candidate_tests(norm_rel: str) -> List[str]:
    """Python 파일 대상 짝꿍 테스트 후보 상대 경로 목록을 생성하는 순수 함수."""
    filename = os.path.basename(norm_rel)
    base_name, _ = os.path.splitext(filename)
    
    if norm_rel.startswith("tests/") and base_name.startswith("test_"):
        return [norm_rel]
    
    candidates = []
    if ".agents/scripts/" in norm_rel or norm_rel.startswith("scripts/"):
        candidates.append(f"tests/test_{base_name}.py")
        return candidates

    if norm_rel.startswith("src/"):
        parts = norm_rel.split("/")
        if len(parts) >= 3:
            domain = parts[1]
            candidates.append(f"tests/{domain}/test_{base_name}.py")
            candidates.append(f"tests/test_{domain}_{base_name}.py")
        candidates.append(f"tests/test_{base_name}.py")
        return candidates

    candidates.append(f"tests/test_{base_name}.py")
    return candidates


def _generate_typescript_candidate_tests(norm_rel: str) -> List[str]:
    """TypeScript/JavaScript 파일 대상 짝꿍 테스트 후보 상대 경로 목록을 생성하는 순수 함수."""
    dir_path = os.path.dirname(norm_rel)
    filename = os.path.basename(norm_rel)
    base_name, ext = os.path.splitext(filename)
    
    if base_name.endswith(".test") or base_name.endswith(".spec"):
        return [norm_rel]

    candidates = []
    if dir_path:
        candidates.append(f"{dir_path}/{base_name}.test{ext}")
        candidates.append(f"{dir_path}/{base_name}.spec{ext}")
    else:
        candidates.append(f"{base_name}.test{ext}")
        candidates.append(f"{base_name}.spec{ext}")

    if norm_rel.startswith("src/"):
        rel_sub = norm_rel[4:]
        sub_dir = os.path.dirname(rel_sub)
        test_ext = ".ts" if ext in [".ts", ".tsx"] else ".js"
        if sub_dir:
            candidates.append(f"tests/{sub_dir}/{base_name}.test{test_ext}")
            candidates.append(f"tests/{sub_dir}/{base_name}.test{ext}")
        candidates.append(f"tests/{base_name}.test{test_ext}")
        candidates.append(f"tests/{base_name}.test{ext}")

    return candidates


def _generate_go_candidate_tests(norm_rel: str) -> List[str]:
    """Go 파일 대상 짝꿍 테스트 후보 상대 경로 목록을 생성하는 순수 함수."""
    dir_path = os.path.dirname(norm_rel)
    filename = os.path.basename(norm_rel)
    base_name, ext = os.path.splitext(filename)

    if base_name.endswith("_test"):
        return [norm_rel]

    if dir_path:
        return [f"{dir_path}/{base_name}_test.go"]
    return [f"{base_name}_test.go"]


def resolve_partner_test_file(
    target_file: str,
    existing_test_files: Optional[Set[str]] = None,
    project_root: str = ""
) -> str:
    """수정 대상 파일을 기반으로 3대 언어(Python, TS, Go) 1:1 짝꿍 핀-테스트를 탐색하는 순수 함수."""
    norm = _normalize_path(target_file)
    if not norm:
        return ""

    _, ext = os.path.splitext(norm)
    ext_lower = ext.lower()

    if ext_lower in BYPASS_EXTENSIONS:
        return ""

    if ext_lower == ".py":
        candidates = _generate_python_candidate_tests(norm)
    elif ext_lower in [".ts", ".tsx", ".js", ".jsx"]:
        candidates = _generate_typescript_candidate_tests(norm)
    elif ext_lower == ".go":
        candidates = _generate_go_candidate_tests(norm)
    else:
        return ""

    if existing_test_files is not None:
        for cand in candidates:
            if cand in existing_test_files:
                return cand
        return ""

    if project_root:
        for cand in candidates:
            abs_cand = os.path.join(project_root, cand)
            if os.path.exists(abs_cand):
                return cand

    return ""


def extract_scoped_test_dirs(
    changed_files: List[str],
    fallback_patterns: Optional[List[str]] = None
) -> Tuple[List[str], bool]:
    """Git Diff 변경 파일 목록을 분석하여 실행할 도메인 테스트 디렉터리를 추출하는 순수 함수."""
    if not changed_files:
        return [], False

    patterns = fallback_patterns if fallback_patterns is not None else DEFAULT_FALLBACK_PATTERNS

    for f in changed_files:
        norm = _normalize_path(f)
        for pat in patterns:
            if pat in norm:
                return [], True

    scoped_dirs: Set[str] = set()

    for f in changed_files:
        norm = _normalize_path(f)
        _, ext = os.path.splitext(norm)
        if ext.lower() in BYPASS_EXTENSIONS:
            continue

        parts = norm.split("/")
        if len(parts) >= 2:
            if parts[0] == "src" and len(parts) >= 3:
                domain = parts[1]
                scoped_dirs.add(f"tests/{domain}")
            elif parts[0] == "tests" and len(parts) >= 3:
                domain = parts[1]
                scoped_dirs.add(f"tests/{domain}")
            elif parts[0] == "tests":
                scoped_dirs.add("tests")

    return sorted(list(scoped_dirs)), False


def run_targeted_partner_test(
    target_rel: str,
    project_root: str,
    python_exe: str = "",
    timeout: int = 5
) -> bool:
    """수정 대상 파일의 1:1 짝꿍 테스트만 정밀 실행하는 1계층 초경량 러너 (신규/무매칭 시 Non-blocking True)."""
    partner_test = resolve_partner_test_file(target_rel, project_root=project_root)
    if not partner_test:
        return True

    import subprocess
    import sys
    py_bin = python_exe or sys.executable
    try:
        proc = subprocess.run(
            [py_bin, "-m", "pytest", "-o", "addopts=", "-q", partner_test],
            cwd=project_root,
            capture_output=True,
            timeout=timeout
        )
        return proc.returncode == 0
    except Exception:
        return False
