# [파일명]: pre_tool_guard_core.py | [용도] PreTool 보안 감찰 판정 순수 코어 (Pure Functional Core)
import os
import re
from typing import Any, Dict, List, Set, Tuple

try:
    from core.common.action_rule_core import (
        format_action_rule,
        VIOLATION_OVERWRITE,
        VIOLATION_PIN_TEST_REQUIRED,
        VIOLATION_REFACTOR_TEST_MUTATION,
        VIOLATION_SANCTUARY,
    )
except ImportError:
    from core.common.action_rule_core import (
        format_action_rule,
        VIOLATION_OVERWRITE,
        VIOLATION_PIN_TEST_REQUIRED,
        VIOLATION_REFACTOR_TEST_MUTATION,
        VIOLATION_SANCTUARY,
    )

DEFAULT_GUARD_CONFIG: Dict[str, Any] = {
    "switches": {
        "block_direct_overwrite": True,
        "require_pin_test_first": True,
        "require_red_test_first": True,
        "instant_syntax_check": True,
        "block_unauthorized_deploy": True,
        "prevent_test_deletion": True
    },
    "blocked_commands": [
        "git push",
        "vercel",
        "vercel --prod",
        "npm publish"
    ],
    "paths": {"src_dir": "src", "test_dir": "tests"},
    "bypass_extensions": [".md", ".canvas", ".txt", ".png", ".jpg", ".jpeg", ".svg", ".ico", ".log", ".json"]
}

from shell.pre_tool.pre_tool_shell import safe_read_stdin



def check_deploy_command(
    command_line: str,
    blocked_commands: List[str],
    block_deploy: bool = True
) -> Tuple[bool, str]:
    """run_command 호출 시 사장님 사전 승인 없는 상용 배포 명령어 여부를 판정하는 순수 함수."""
    if not block_deploy:
        return True, ""

    cmd = (command_line or "").strip()
    for blocked in blocked_commands:
        if blocked in cmd:
            reason = (
                f"[PreTool 차단: 상용 배포 명령어 사전 승인 필요]\n"
                f"실행 시도 명령어: '{cmd}'\n"
                f"감지된 배포 키워드: '{blocked}'\n"
                f"사유: 상용 서비스 배포(Git Push / Vercel Deploy)는 반드시 사장님의 사전 결재가 필수입니다.\n"
                f"조치 요령: 배포를 진행하려면 먼저 사장님께 배포 승인 요청 보고를 올리고 승인을 획득하세요."
            )
            return False, reason
    return True, ""


def is_sanctuary_file(norm_rel_path: str) -> bool:
    """중앙 조종석 성역 파일(guard_config.json, hooks.json, scripts/ 등)인지 판정하는 순수 함수."""
    norm = norm_rel_path.replace("\\", "/").lstrip("/")
    if norm.endswith("guard_config.json") or "guard_config" in norm:
        return True
    if norm.endswith("hooks.json") or "hooks.json" in norm:
        return True
    if norm.startswith(".agents/scripts") or "/.agents/scripts" in norm:
        return True
    return False


def is_bypass_extension(ext: str, bypass_exts: Set[str]) -> bool:
    """문서 및 정적 파일 스마트 패스 대상인지 판정하는 순수 함수."""
    return ext.lower() in bypass_exts


def check_overwrite_violation(
    tool_name: str,
    file_exists: bool,
    target_rel: str
) -> Tuple[bool, str]:
    """write_to_file 호출 시 기존 파일 덮어쓰기 위반 여부를 판정하는 순수 함수."""
    if tool_name == "write_to_file" and file_exists:
        action_rule = format_action_rule(VIOLATION_OVERWRITE, {"target_file": target_rel})
        reason = (
            f"[PreTool 차단: 기존 파일 덮어쓰기 금지]\n"
            f"대상 파일 '{target_rel}'은 이미 존재하는 파일입니다.\n"
            f"기존 정상 로직 및 주석 유실을 방지하기 위해 write_to_file 호출이 거부되었습니다.\n"
            f"{action_rule}"
        )
        return False, reason
    return True, ""


try:
    from core.common.stack_detector_core import is_test_file_for_stack, check_multistack_test_deletion
except ImportError:
    from core.common.stack_detector_core import is_test_file_for_stack, check_multistack_test_deletion


def check_test_deletion_violation(
    old_code: str,
    target_code: str,
    replacement_code: str,
    target_rel: str
) -> Tuple[bool, str]:
    """tests/ 수정 시 기존 테스트 케이스의 임의 삭제/약화 여부를 정규식으로 분석하는 순수 함수 (다중 언어 지원)."""
    return check_multistack_test_deletion(old_code, target_code, replacement_code, target_rel)


def check_pin_test_requirement(
    norm_rel_path: str,
    changed_files: List[str],
    has_root_src: bool = True
) -> Tuple[bool, List[str], str]:
    """src/ 및 하위 서브프로젝트 비즈니스 코드 수정 시 핀-테스트 선행 작성 여부를 판정하는 순수 함수.
    
    만약 프로젝트 루트에 src/ 디렉터리가 없는 훅 개발 환경(has_root_src=False)일 경우,
    .agents/scripts/ 자체를 비즈니스 코드로 자동 승격하여 핀-테스트를 강제합니다.
    """
    norm = norm_rel_path.replace("\\", "/")
    # 비즈니스 소스 코드 경로 식별 (루트 src/, 서브폴더 내 src/, 또는 훅 개발 환경의 .agents/scripts/)
    is_biz_source = norm.startswith("src/") or "/src/" in norm
    if not has_root_src and norm.startswith(".agents/scripts/"):
        is_biz_source = True

    if not is_biz_source:
        return True, [], ""

    # 다중 스택(Python, TypeScript, Go) 핀-테스트 변경 감지
    test_changes = [
        f for f in changed_files
        if (
            is_test_file_for_stack(f.replace("\\", "/"), "python")
            or is_test_file_for_stack(f.replace("\\", "/"), "typescript")
            or is_test_file_for_stack(f.replace("\\", "/"), "go")
        )
    ]

    if not test_changes:
        target_name = "비즈니스 코드" if not norm.startswith(".agents/scripts/") else "방탄 훅 코어 코드"
        action_rule = format_action_rule(VIOLATION_PIN_TEST_REQUIRED, {"target_file": norm_rel_path})
        reason = (
            f"[PreTool 차단: 핀-테스트 선행 작성 원칙 위반]\n"
            f"{target_name} '{norm_rel_path}'를 수정하기 전에, 반드시 테스트 코드(tests/ 또는 *.test.ts)를 먼저 작성하세요.\n"
            f"{action_rule}"
        )
        return False, [], reason

    return True, test_changes, ""


def evaluate_multi_test_red_status(
    test_files: List[str],
    verifier_fn: Any
) -> Tuple[bool, str, str]:
    """복수 테스트 변경 파일들을 순회하며, 최소 1개 이상의 진짜 비즈니스 Red가 존재하는지 검증하는 순수 함수.
    
    Returns:
        (has_red, verified_red_test_path, last_reject_reason)
    """
    if not test_files:
        return False, "", "테스트 파일이 지정되지 않았습니다."

    last_reason = ""
    for test_file in test_files:
        is_red, reject_reason = verifier_fn(test_file)
        if is_red:
            return True, test_file, ""
        last_reason = reject_reason

    return False, "", last_reason


def check_refactor_mode_eligibility(
    target_rel_path: str,
    target_file_line_count: int,
    changed_files: List[str],
    all_tests_green: bool,
    work_mode: str = "default",
    line_limit: int = 300
) -> Tuple[bool, str]:
    """300줄 초과 모듈 감축 또는 명시적 refactor 모드 시 기존 테스트 100% Green을 조건으로 리팩토링을 허용하는 순수 판정 함수."""
    is_line_overflow = target_file_line_count > line_limit
    is_refactor_work = (work_mode or "").lower().strip() == "refactor"

    if not (is_line_overflow or is_refactor_work):
        return False, "[PreTool 차단: 리팩토링 대상 아님] 대상 파일이 300줄 이하이며 명시적 리팩토링 모드가 아닙니다."

    # 테스트 파일 변경 여부 확인 (Zero Mutation: 리팩토링 중 테스트 코드 수정 일절 금지)
    has_test_changes = any(
        (
            is_test_file_for_stack(f.replace("\\", "/"), "python")
            or is_test_file_for_stack(f.replace("\\", "/"), "typescript")
            or is_test_file_for_stack(f.replace("\\", "/"), "go")
        )
        for f in changed_files
    )
    if has_test_changes:
        action_rule = format_action_rule(VIOLATION_REFACTOR_TEST_MUTATION)
        return False, (
            "[PreTool 차단: 리팩토링 중 테스트 변경 감지]\n"
            "리팩토링 중에는 기존 테스트 코드를 일절 변경할 수 없습니다 (Zero Mutation).\n"
            f"{action_rule}"
        )

    if not all_tests_green:
        return False, (
            "[PreTool 차단: 기존 회귀 테스트 실패]\n"
            "리팩토링을 진행하려면 기존의 모든 테스트가 100% Green(통과) 상태여야 합니다.\n"
            "먼저 실패한 테스트를 해결한 후 리팩토링을 시도하세요."
        )

    return True, ""


def orchestrate_refactor_gate(
    target_abs: str,
    norm_rel: str,
    guard_config: Dict[str, Any],
    changed_files: List[str],
    test_runner_fn: Any,
    work_mode: str = "default"
) -> Tuple[bool, bool, str]:
    """리팩토링 게이트 해당 여부를 종합 조율하고 (is_candidate, is_allowed, reason)을 반환하는 순수 함수."""
    target_line_count = 0
    if os.path.exists(target_abs):
        try:
            with open(target_abs, "r", encoding="utf-8", errors="ignore") as f:
                target_line_count = len(f.readlines())
        except Exception:
            pass

    arch_policy = guard_config.get("architecture_policy", {})
    line_limit = arch_policy.get("max_line_limit", 300)
    enforce_pretool = arch_policy.get("enforce_in_pretool", False)
    mode = (work_mode or "").strip().lower()

    should_check_line = enforce_pretool and (target_line_count > line_limit)
    if should_check_line or mode == "refactor":
        all_green = test_runner_fn() if callable(test_runner_fn) else False
        is_ok, reason = check_refactor_mode_eligibility(
            target_rel_path=norm_rel,
            target_file_line_count=target_line_count,
            changed_files=changed_files,
            all_tests_green=all_green,
            work_mode=mode,
            line_limit=line_limit
        )
        return True, is_ok, reason

    return False, False, ""
