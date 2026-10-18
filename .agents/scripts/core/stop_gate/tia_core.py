# [파일명]: tia_core.py | [용도] 3단계 계층형 테스트 아키텍처(TIA) 3대 언어 짝꿍 탐색 및 도메인 추출 순수 코어
import os
import re
from typing import List, Optional, Set, Tuple

DEFAULT_FALLBACK_PATTERNS: List[str] = [
    "shared/", "/shared/", "core/constants.py", "constants.py",
    "types/", "/types/", "guard_config.json", "hooks.json"
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
        return [f"tests/test_{base_name}.py"]
    if norm_rel.startswith("src/"):
        parts = norm_rel.split("/")
        if len(parts) >= 4 and parts[1] == "features":
            d = parts[2]
            candidates.extend([f"tests/test_features/{d}/test_pin_{base_name}.py", f"tests/test_features/{d}/test_{base_name}.py", f"tests/{d}/test_{base_name}.py"])
        elif len(parts) >= 3:
            d = parts[1]
            candidates.extend([f"tests/{d}/test_{base_name}.py", f"tests/test_{d}_{base_name}.py"])
    candidates.append(f"tests/test_{base_name}.py")
    return candidates


def _score_test_match(target_norm: str, test_path: str) -> int:
    """수정 대상 파일과 테스트 파일 간의 의미 토큰 적합도 점수(0~100)를 계산하는 순수 함수."""
    t_norm = test_path.replace("\\", "/").lower()
    t_file = os.path.splitext(os.path.basename(t_norm))[0]
    parts = [p.lower() for p in target_norm.split("/") if p not in ("src", "shell", "core", "adapters", "pkg", "modules", "backend", "app", "features")]
    if not parts:
        return 0
    base = os.path.splitext(parts[-1])[0]
    domains = parts[:-1]
    if base not in t_file:
        return 0
    if domains and not any(d in t_norm for d in domains):
        return 0
    score = 50
    if domains and any(d in t_norm for d in domains):
        score += 30
    if t_file.startswith("test_pin_"):
        score += 20
    return score


def _generate_typescript_candidate_tests(norm_rel: str) -> List[str]:
    """TypeScript/JavaScript 파일 대상 짝꿍 테스트 후보 상대 경로 목록을 생성하는 순수 함수."""
    dir_path = os.path.dirname(norm_rel)
    filename = os.path.basename(norm_rel)
    base_name, ext = os.path.splitext(filename)
    
    if base_name.endswith(".test") or base_name.endswith(".spec"):
        return [norm_rel]

    candidates = []
    if dir_path:
        candidates.extend([f"{dir_path}/{base_name}.test{ext}", f"{dir_path}/{base_name}.spec{ext}"])
    else:
        candidates.extend([f"{base_name}.test{ext}", f"{base_name}.spec{ext}"])

    if norm_rel.startswith("src/"):
        rel_sub = norm_rel[4:]
        sub_dir = os.path.dirname(rel_sub)
        test_ext = ".ts" if ext in [".ts", ".tsx"] else ".js"
        if sub_dir:
            candidates.extend([f"tests/{sub_dir}/{base_name}.test{test_ext}", f"tests/{sub_dir}/{base_name}.test{ext}"])
        candidates.extend([f"tests/{base_name}.test{test_ext}", f"tests/{base_name}.test{ext}"])

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
        best_cand, best_score = "", 70
        for tf in existing_test_files:
            score = _score_test_match(norm, tf)
            if score > best_score:
                best_cand, best_score = tf, score
        return best_cand

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
            if parts[0] == "src":
                if len(parts) >= 4 and parts[1] == "features":
                    domain = parts[2]
                    scoped_dirs.add(f"tests/test_features/{domain}")
                elif len(parts) >= 3:
                    domain = parts[1]
                    scoped_dirs.add(f"tests/{domain}")
            elif parts[0] == "tests":
                if len(parts) >= 4 and parts[1] == "test_features":
                    domain = parts[2]
                    scoped_dirs.add(f"tests/test_features/{domain}")
                elif len(parts) >= 3:
                    domain = parts[1]
                    scoped_dirs.add(f"tests/{domain}")
                else:
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


def resolve_tia_test_targets(
    changed_files: List[str],
    guard_config: Optional[dict] = None,
    existing_tests: Optional[Set[str]] = None,
    project_root: str = ""
) -> Tuple[List[str], bool]:
    """guard_config의 tia_policy에 따라 2계층 테스트 대상(짝꿍/도메인) 및 전체 폴백 여부를 확정하는 순수 함수."""
    if not changed_files:
        return [], False

    cfg = guard_config or {}
    tia_policy = cfg.get("tia_policy", {})
    mode = tia_policy.get("mode", "domain_first")
    enable_fallback = tia_policy.get("enable_fallback_all_tests", True)
    fallback_patterns = tia_policy.get("fallback_patterns", DEFAULT_FALLBACK_PATTERNS)

    # 1. full_always 모드: 무조건 전체 폴백
    if mode == "full_always":
        return [], True

    # 2. 0순위 공통 모듈 검문: fallback_patterns 일치 파일 존재 시 무조건 전체 폴백
    for f in changed_files:
        norm = _normalize_path(f)
        for pat in fallback_patterns:
            if pat in norm:
                return [], True

    # 3. partner_first 모드: 1:1 짝꿍 파일 우선 탐색 (단일 및 복수 파일 대차평형 보장)
    if mode == "partner_first":
        partner_targets: Set[str] = set()
        unmatched_files: List[str] = []
        for f in changed_files:
            norm = _normalize_path(f)
            _, ext = os.path.splitext(norm)
            if ext.lower() in BYPASS_EXTENSIONS:
                continue

            partner = resolve_partner_test_file(
                f,
                existing_test_files=existing_tests,
                project_root=project_root
            )
            if partner:
                partner_targets.add(partner)
            else:
                unmatched_files.append(f)

        # 모든 파일이 짝꿍 매칭 성공한 경우
        if partner_targets and not unmatched_files:
            return sorted(list(partner_targets)), False

        # 일부 파일만 짝꿍 매칭되었거나 미매칭 파일이 섞인 경우: 미매칭 파일들의 도메인 스코프를 보충 수집
        if unmatched_files:
            unmatched_dirs, is_fb = extract_scoped_test_dirs(unmatched_files, fallback_patterns)
            if is_fb:
                return [], True
            if unmatched_dirs:
                combined = sorted(list(partner_targets.union(set(unmatched_dirs))))
                return combined, False
            if partner_targets:
                return sorted(list(partner_targets)), False

        # 둘 다 없으면 enable_fallback_all_tests 스위치 대조
        return [], enable_fallback

    # 4. domain_first 모드 (기본값): 도메인 스코프 디렉터리 추출
    scoped_dirs, is_fb = extract_scoped_test_dirs(changed_files, fallback_patterns)
    if is_fb:
        return [], True
    if scoped_dirs:
        return scoped_dirs, False

    # 도메인 매칭 실패 시 enable_fallback_all_tests 스위치 대조
    return [], enable_fallback
