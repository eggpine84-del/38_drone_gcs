# [파일명]: test_mutation_core.py | [용도] 4대 작업 모드별 테스트 변형/삭제 통제 순수 코어 (Pure Functional Core)
import os
import ast
import re
from typing import Any, Dict, List, Optional, Tuple


def check_mock_pass_assertions(code_content: str) -> Tuple[bool, str]:
    """테스트 함수 내 assert True, pass 단독 등 깡통 단언문(Mock-Pass) 꼼수를 AST로 감찰하는 순수 함수."""
    if not code_content or not code_content.strip():
        return True, ""
    try:
        tree = ast.parse(code_content)
    except Exception:
        return True, ""

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if not node.name.startswith("test_"):
                continue

            # docstring 제외한 실제 실행 구문 추출
            body = []
            for stmt in node.body:
                if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant) and isinstance(stmt.value.value, str):
                    continue
                body.append(stmt)

            if not body:
                return False, f"[테스트 게이트 차단] 함수 '{node.name}'에 본문이 비어있습니다 (유효 단언문 필수)."

            if len(body) == 1 and isinstance(body[0], ast.Pass):
                return False, f"[테스트 게이트 차단] 함수 '{node.name}'에 단독 pass 꼼수가 감지되었습니다 (유효 단언문 필수)."

            for stmt in body:
                if isinstance(stmt, ast.Assert):
                    if isinstance(stmt.test, ast.Constant) and stmt.test.value is True:
                        return False, f"[테스트 게이트 차단] 함수 '{node.name}'에 무의미한 'assert True' 꼼수가 감지되었습니다."

    return True, ""


def _count_code_assertions(code: str) -> int:
    """코드 내 assert 문 개수를 카운트하는 순수 헬퍼 함수."""
    if not code:
        return 0
    try:
        tree = ast.parse(code)
        return sum(1 for node in ast.walk(tree) if isinstance(node, ast.Assert))
    except Exception:
        return len(re.findall(r"\bassert\b", code))


def check_assertion_collapse(
    old_code: str,
    new_code: str,
    max_collapse_ratio: float = 0.3
) -> Tuple[bool, str]:
    """단언문 개수가 허용 비율(기본 30%) 이상 급감(소멸)하는지 감찰하는 순수 함수."""
    old_count = _count_code_assertions(old_code)
    new_count = _count_code_assertions(new_code)
    if old_count == 0:
        return True, ""
    if new_count < old_count:
        loss = old_count - new_count
        ratio = loss / old_count
        if ratio > max_collapse_ratio:
            return False, (
                f"[테스트 게이트 차단: 단언문 급감 감지]\n"
                f"기존 {old_count}개 ➔ 수정 후 {new_count}개 ({loss}개 소실, {ratio*100:.1f}% 감소 > 허용 한도 {max_collapse_ratio*100:.0f}%)\n"
                f"철칙: 낡은 단언문 교체는 허용되나, 핵심 검증 시나리오의 대량 삭제는 엄격히 금지됩니다."
            )
    return True, ""


def evaluate_test_mutation_by_policy(
    work_mode: str,
    deleted_mutations: List[str],
    changed_files: List[str],
    policy: Optional[Dict[str, Any]] = None,
    test_file_diffs: Optional[Dict[str, str]] = None,
    test_file_contents: Optional[Dict[str, Tuple[str, str]]] = None,
    format_mutation_reason_fn: Optional[Any] = None
) -> Tuple[bool, str]:
    """Table-Driven 정책에 따라 테스트 코드 삭제/수정 허용 여부를 결정하는 순수 함수."""
    if not deleted_mutations:
        return True, ""

    cfg = policy or {}
    default_rule = cfg.get("default_rule", "strict_zero_mutation")
    mode_rules = cfg.get("mode_rules", {})
    current_rule = mode_rules.get((work_mode or "").strip().lower(), default_rule)

    def _fallback_reason(dels: List[str]) -> str:
        if callable(format_mutation_reason_fn):
            return format_mutation_reason_fn(dels)
        return f"[테스트 게이트 차단: 기존 테스트 코드 임의 변형/삭제 감지] {', '.join(dels)}"

    if current_rule == "strict_zero_mutation":
        return False, _fallback_reason(deleted_mutations)

    if current_rule == "scoped_ast_guard":
        scoped_cfg = cfg.get("scoped_ast_policy", {})
        max_collapse = scoped_cfg.get("max_assertion_collapse_ratio", 0.3)
        block_mock = scoped_cfg.get("block_mock_pass", True)

        # 1. 대상 파일 국소화 (Target File Pinpoint) 검사
        mutated_test_files: List[str] = []
        for item in deleted_mutations:
            fpath = item.split()[0] if item else ""
            if fpath:
                mutated_test_files.append(fpath.replace("\\", "/"))

        dirty_sources = [
            f.replace("\\", "/") for f in changed_files
            if not (f.replace("\\", "/").startswith("tests/") or "/tests/" in f.replace("\\", "/"))
        ]
        source_basenames = {
            os.path.splitext(os.path.basename(s))[0].lower()
            for s in dirty_sources
        }

        for tfile in mutated_test_files:
            t_base = os.path.splitext(os.path.basename(tfile))[0].lower().replace("test_", "").replace("_test", "")
            is_mapped = any(t_base in s_base or s_base in t_base for s_base in source_basenames) if source_basenames else False
            if not is_mapped and dirty_sources:
                return False, (
                    f"[테스트 게이트 차단: 무관한 테스트 수정 감지 (국소화 위반)]\n"
                    f"수정된 비즈니스 코드({dirty_sources})와 무관한 테스트 파일 '{tfile}'의 삭제는 허용되지 않습니다.\n"
                    f"스펙 변경 시 오직 대상 기능에 매핑된 테스트 파일만 수정할 수 있습니다."
                )

        # 2. AST 가짜 단언문 및 단언문 급감 검사
        contents = test_file_contents or {}
        for tfile in mutated_test_files:
            if tfile in contents:
                old_c, new_c = contents[tfile]
                if block_mock:
                    ok, reason = check_mock_pass_assertions(new_c)
                    if not ok:
                        return False, reason
                ok, reason = check_assertion_collapse(old_c, new_c, max_collapse_ratio=max_collapse)
                if not ok:
                    return False, reason

        return True, ""

    return False, _fallback_reason(deleted_mutations)


CHANGE_TOKEN_NAME = ".change_token"


def determine_work_mode(
    token_exists: bool,
    env_mode: str = "",
    cfg_mode: str = ""
) -> str:
    """1회용 change_token 존재 여부와 환경변수, 설정값을 종합하여 작업 모드를 결정하는 순수 함수 (Table-Driven Coalesce)."""
    valid_modes = {"feat", "change", "fix", "refactor"}
    e_mode = (env_mode or "").strip().lower()
    c_mode = (cfg_mode or "").strip().lower()
    candidates = (
        "change" if token_exists else "",
        e_mode if e_mode in valid_modes else "",
        c_mode if c_mode in valid_modes else "",
        "default"
    )
    return next(m for m in candidates if m)


def resolve_work_mode(project_root: str, guard_config: Optional[Dict[str, Any]] = None) -> str:
    """단일 진실 공급원(SSOT): project_root와 설정을 바탕으로 최종 작업 모드를 판정하는 통합 함수."""
    token_path = os.path.join(project_root, ".agents", CHANGE_TOKEN_NAME)
    token_exists = os.path.exists(token_path)
    env_mode = os.environ.get("GIT_WORK_MODE", "").strip().lower()
    cfg = guard_config or {}
    cfg_mode = cfg.get("current_work_mode", "").strip().lower()
    return determine_work_mode(token_exists=token_exists, env_mode=env_mode, cfg_mode=cfg_mode)


def should_cleanup_change_token(deleted_mutations: Optional[List[str]] = None) -> bool:
    """Git 상에 테스트 삭제 내역(deleted_mutations)이 남아있으면 자폭 보류(False), 커밋 완료(Clean) 시 자폭 허용(True)하는 순수 함수."""
    return not bool(deleted_mutations)


def cleanup_change_token(token_file_path: str) -> None:
    """테스트 Green 통과 직후 1회용 change_token을 안전하게 자폭(삭제)하는 멱등적 I/O 함수."""
    if token_file_path and os.path.exists(token_file_path):
        try:
            os.remove(token_file_path)
        except Exception:
            pass


def handle_test_mutation_gate(
    project_root: str,
    deleted_mutations: List[str],
    changed_files: List[str],
    guard_config: Dict[str, Any]
) -> Tuple[bool, str]:
    """Stop 게이트에서 테스트 삭제 목록과 변경 파일을 수집하여 Table-Driven 정책으로 판정하는 조율 함수."""
    import subprocess
    work_mode = resolve_work_mode(project_root=project_root, guard_config=guard_config)
    mutation_policy = guard_config.get("test_mutation_policy", {})

    test_contents: Dict[str, Tuple[str, str]] = {}
    for item in deleted_mutations:
        fpath = item.split()[0].replace("\\", "/")
        abs_p = os.path.join(project_root, fpath)
        if os.path.exists(abs_p):
            try:
                with open(abs_p, "r", encoding="utf-8", errors="replace") as f:
                    new_c = f.read()
                show_proc = subprocess.run(
                    ["git", "show", f"HEAD:{fpath}"],
                    cwd=project_root,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace"
                )
                old_c = show_proc.stdout if show_proc.returncode == 0 else ""
                test_contents[fpath] = (old_c, new_c)
            except Exception:
                pass

    return evaluate_test_mutation_by_policy(
        work_mode=work_mode,
        deleted_mutations=deleted_mutations,
        changed_files=changed_files,
        policy=mutation_policy,
        test_file_contents=test_contents
    )

