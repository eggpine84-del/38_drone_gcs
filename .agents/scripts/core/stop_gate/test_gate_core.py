# [파일명]: test_gate_core.py | [용도] Stop 테스트 게이트 감찰 판정 순수 코어 (Pure Functional Core)
import os
import ast
import re
from typing import Any, Dict, List, Optional, Set, Tuple

DEFAULT_DOC_EXTS: Set[str] = {
    ".md", ".canvas", ".txt", ".png", ".jpg", ".jpeg", ".svg", ".ico", ".log"
}


def is_only_doc_changes(
    changed_files: List[str],
    doc_exts: Optional[Set[str]] = None
) -> bool:
    """변경된 파일들이 순수 비코드(문서/이미지/로그)만 포함하는지 판정하는 순수 함수."""
    if not changed_files:
        return False
    target_exts = doc_exts if doc_exts is not None else DEFAULT_DOC_EXTS
    return all(os.path.splitext(f)[1].lower() in target_exts for f in changed_files)


def extract_dirty_source_files(changed_files: List[str]) -> List[str]:
    """변경된 파일 목록 중 문서 및 테스트 코드를 제외한 실제 비즈니스/스크립트 소스코드만 추출하는 순수 함수."""
    dirty_sources: List[str] = []
    for f in changed_files:
        norm = f.replace("\\", "/").lower()
        if is_only_doc_changes([f]):
            continue
        if norm.startswith("tests/") or "/tests/" in norm or "test_" in norm or "_test." in norm or ".test." in norm:
            continue
        dirty_sources.append(f)
    return dirty_sources


def parse_git_numstat_for_deletions(numstat_output: str) -> List[str]:
    """git diff --numstat 결과 텍스트에서 삭제(-) 라인이 발생한 파일 목록을 파싱하는 순수 함수."""
    deleted_mutations: List[str] = []
    if not numstat_output or not numstat_output.strip():
        return deleted_mutations

    for line in numstat_output.splitlines():
        parts = line.strip().split()
        if len(parts) >= 3:
            added_str, deleted_str, file_path = parts[0], parts[1], parts[2]
            if deleted_str.isdigit() and int(deleted_str) > 0:
                deleted_mutations.append(f"{file_path} (삭제: -{deleted_str}줄)")
    return deleted_mutations


def format_test_mutation_reason(deleted_mutations: List[str]) -> str:
    """테스트 변형/삭제 감지 시 에러 메시지를 생성하는 순수 함수."""
    mutation_msg = ", ".join(deleted_mutations)
    return (
        f"[테스트 게이트 차단: 기존 테스트 코드 임의 변형/삭제 감지]\n"
        f"감지된 위반 파일: {mutation_msg}\n"
        f"철칙: 기존 테스트 코드는 절대 삭제하거나 조건을 약화시킬 수 없습니다 (Zero Mutation).\n"
        f"삭제된 테스트 라인을 즉시 원래대로 복구하고, 오직 소스 코드를 수정하여 통과시키세요."
    )


def resolve_test_runner_command(
    project_has_package_json: bool,
    project_has_cargo_toml: bool,
    project_has_gomod: bool,
    project_has_python_tests: bool,
    is_win32: bool,
    python_exe: str = "python"
) -> Tuple[str, List[str], bool]:
    """프로젝트 파일 구성 플래그를 기반으로 적합한 언어별 테스트 러너 명령어를 결정하는 순수 함수 (Table-Driven)."""
    if project_has_package_json:
        return "npm test", ["npm", "test"], is_win32
    if project_has_cargo_toml:
        return "cargo test", ["cargo", "test"], is_win32
    if project_has_gomod:
        return "go test", ["go", "test", "./..."], is_win32
    if project_has_python_tests:
        return "pytest", [python_exe, "-m", "pytest", "-q"], False
    return "", [], False


def resolve_fallback_single_runner(
    project_root: str,
    is_win32: bool,
    python_exe: str = "python"
) -> List[Dict[str, Any]]:
    """다중 러너 미감지 시 기존 단일 러너 레거시 폴백을 생성하는 순수 함수."""
    has_pkg_json = os.path.exists(os.path.join(project_root, "package.json"))
    has_cargo = os.path.exists(os.path.join(project_root, "Cargo.toml"))
    has_gomod = os.path.exists(os.path.join(project_root, "go.mod"))
    has_py = (
        os.path.exists(os.path.join(project_root, "tests"))
        or os.path.exists(os.path.join(project_root, "pytest.ini"))
        or os.path.exists(os.path.join(project_root, "pyproject.toml"))
    )

    runner_name, test_cmd, use_shell = resolve_test_runner_command(
        project_has_package_json=has_pkg_json,
        project_has_cargo_toml=has_cargo,
        project_has_gomod=has_gomod,
        project_has_python_tests=has_py,
        is_win32=is_win32,
        python_exe=python_exe
    )
    if test_cmd:
        return [{
            "name": runner_name,
            "cmd": test_cmd,
            "cwd": project_root,
            "use_shell": use_shell
        }]
    return []


def filter_violating_line_limit_files(
    file_line_counts: Dict[str, int],
    limit: int = 300
) -> List[str]:
    """파일별 라인 수 매핑에서 한도(300줄)를 초과한 모듈 목록을 필터링하는 순수 함수."""
    violations: List[str] = []
    for rel_path, line_count in file_line_counts.items():
        if line_count > limit:
            violations.append(f"{rel_path} ({line_count}줄 > {limit}줄 한도)")
    return violations


def format_line_limit_violation_reason(violating_files: List[str]) -> str:
    """300줄 초과 모듈 감지 시 에러 메시지를 생성하는 순수 함수."""
    viol_list = "\n".join(violating_files)
    return (
        f"[아키텍처 게이트 차단: 300줄 초과 모듈 감지]\n"
        f"{viol_list}\n\n"
        f"철칙: 300줄 초과 감지 시 억지 줄바꿈 축소는 절대 금지됩니다.\n"
        f"파이프라인 규칙에 따라 [refactor 모드]로 자동 전환하여 서브 모듈 분리(SRP)를 수행하세요."
    )


def format_test_failure_reason(
    runner_name: str,
    returncode: int,
    output_tail: str,
    dirty_source_files: Optional[List[str]] = None
) -> str:
    """테스트 러너 실행 실패 시 에러 피드백 메시지를 생성하는 순수 함수."""
    base_msg = (
        f"[테스트 게이트 차단: {runner_name} 미통과 (Exit Code {returncode})]\n"
        f"테스트가 실패하여 작업을 완료할 수 없습니다.\n"
        f"철칙: 테스트 코드는 절대 변형·삭제·스킵·약화시키지 말고, 모든 테스트를 100% Pass 시키세요.\n"
    )
    if dirty_source_files:
        files_str = " ".join(dirty_source_files)
        rollback_msg = (
            f"\n[자가치유 안내: 롤백 우선]\n"
            f"최근 수정한 소스 파일로 인해 기존 회귀 테스트가 깨졌다면, 추가 코드 수정을 즉시 중단하고 run_command로 아래 명령어를 실행하여 오염 파일을 원복(Rollback)하세요:\n"
            f"git restore {files_str}\n"
        )
        base_msg += rollback_msg
    else:
        base_msg += f"안내: 신규 기능 핀-테스트를 정상 구현하여 통과시키거나, 실패 원인을 정밀 수리하세요.\n"

    return f"{base_msg}\n--- {runner_name} 실패 로그 요약 ---\n{output_tail}"


def check_architecture_line_limits(
    project_root: str,
    cfg: Dict
) -> Tuple[bool, str]:
    """설정 기반으로 소스 디렉터리의 라인 수를 집계하고 300줄 초과 여부를 판정하는 순수 위임 함수."""
    switches = cfg.get("switches", {})
    if not switches.get("enforce_line_limit", False):
        return True, ""

    policy = cfg.get("architecture_policy", {})
    limit = policy.get("max_line_limit", 300)
    target_dirs = list(policy.get("target_dirs", ["src"]))
    if not os.path.exists(os.path.join(project_root, "src")):
        if ".agents/scripts" not in target_dirs:
            target_dirs.append(".agents/scripts")

    try:
        from core.stop_gate.multistack_scanner_core import collect_all_source_dirs, scan_multistack_line_counts
    except ImportError:
        from core.stop_gate.multistack_scanner_core import collect_all_source_dirs, scan_multistack_line_counts

    all_source_dirs = collect_all_source_dirs(project_root, target_dirs)
    file_line_counts = scan_multistack_line_counts(project_root, all_source_dirs)

    violating_files = filter_violating_line_limit_files(file_line_counts, limit=limit)
    if violating_files:
        return False, format_line_limit_violation_reason(violating_files)
    return True, ""

# test_mutation_core 순수 로직 임포트 및 Facade 재노출 (하위 호환성 100% 유지)
try:
    from core.stop_gate.test_mutation_core import (
        check_mock_pass_assertions,
        check_assertion_collapse,
        evaluate_test_mutation_by_policy,
        handle_test_mutation_gate,
        determine_work_mode,
        cleanup_change_token,
        should_cleanup_change_token,
    )
except ImportError:
    from core.stop_gate.test_mutation_core import (
        check_mock_pass_assertions,
        check_assertion_collapse,
        evaluate_test_mutation_by_policy,
        handle_test_mutation_gate,
        determine_work_mode,
        cleanup_change_token,
        should_cleanup_change_token,
    )



# circuit_breaker_core 순수 로직 임포트 및 Facade 재노출 (하위 호환성 100% 유지)
try:
    from core.stop_gate.circuit_breaker_core import (
        parse_test_failure_hybrid,
        evaluate_circuit_breaker_state,
        reset_circuit_breaker,
        handle_test_failure_orchestration,
    )
except ImportError:
    from core.stop_gate.circuit_breaker_core import (
        parse_test_failure_hybrid,
        evaluate_circuit_breaker_state,
        reset_circuit_breaker,
        handle_test_failure_orchestration,
    )


def finalize_gate(
    decision: str,
    reason: str = "",
    project_root: str = "",
    deleted_mutations: Optional[List[str]] = None
) -> None:
    """단일 출구 관문(Single Exit Gate): 토큰 자폭 및 응답 출력을 1곳에서 원자적으로 처리하는 통합 함수."""
    import json
    if decision == "allow":
        if project_root and should_cleanup_change_token(deleted_mutations):
            token_file = os.path.join(project_root, ".agents", ".change_token")
            cleanup_change_token(token_file)
        if project_root:
            cache_file = os.path.join(project_root, ".agents", ".red_verified_cache.json")
            try:
                from core.pre_tool.red_cache_core import clear_red_cache
                clear_red_cache(cache_file)
            except Exception:
                pass


    payload = {"decision": decision}
    if reason:
        payload["reason"] = reason
    print(json.dumps(payload, ensure_ascii=False))

