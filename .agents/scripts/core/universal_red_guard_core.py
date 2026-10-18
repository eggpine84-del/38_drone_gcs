# [파일명]: universal_red_guard_core.py | [용도] 다국어 스택 Red 판정 순수 코어 (Pure Functional Core)
import os
import re
from typing import Tuple, Dict, List

try:
    from core.action_rule_core import (
        format_action_rule,
        VIOLATION_DUMMY_ASSERTION,
        VIOLATION_SYNTAX_ERROR_RED,
    )
except ImportError:
    from .action_rule_core import (
        format_action_rule,
        VIOLATION_DUMMY_ASSERTION,
        VIOLATION_SYNTAX_ERROR_RED,
    )

DUMMY_ASSERTION_PATTERNS: Dict[str, List[Tuple[str, str]]] = {
    "python": [
        (r"assert\s+False\b", "assert False"),
        (r"assert\s+0\b", "assert 0"),
        (r"assert\s+1\s*==\s*2\b", "assert 1 == 2"),
        (r"self\.assertTrue\(\s*False\s*\)", "self.assertTrue(False)"),
        (r"self\.assertEqual\(\s*1\s*,\s*2\s*\)", "self.assertEqual(1, 2)"),
    ],
    "node": [
        (r"expect\(\s*false\s*\)\.toBe\(\s*true\s*\)", "expect(false).toBe(true)"),
        (r"expect\(\s*1\s*\)\.toBe\(\s*2\s*\)", "expect(1).toBe(2)"),
        (r"assert\.fail\(", "assert.fail()"),
    ],
    "go": [
        (r"t\.Fail\(\)", "t.Fail()"),
        (r"panic\(\s*[\"']test[\"']\s*\)", "panic('test')"),
    ],
    "rust": [
        (r"assert!\(\s*false\s*\)", "assert!(false)"),
        (r"panic!\(\s*[\"']test[\"']\s*\)", "panic!('test')"),
    ]
}

FAKE_RED_SIGNATURES: Dict[str, List[str]] = {
    "python": ["ImportError:", "ModuleNotFoundError:", "SyntaxError:"],
    "node": ["Cannot find module", "SyntaxError:", "ReferenceError:"],
    "go": ["undefined:", "cannot find package", "syntax error"],
    "rust": ["cannot find", "unresolved import", "syntax error"]
}

REAL_RED_SIGNATURES: Dict[str, List[str]] = {
    "python": ["AssertionError", "FAILED"],
    "node": ["Expected:", "AssertionError", "FAIL"],
    "go": ["--- FAIL:", "FAIL"],
    "rust": ["assertion failed", "FAILED"]
}


def _check_dummy_assertions(test_content: str, stack: str) -> Tuple[bool, str]:
    """언어별 더미 자해 단언문(assert False 등) 정적 검사 순수 함수."""
    target_patterns = DUMMY_ASSERTION_PATTERNS.get(stack, DUMMY_ASSERTION_PATTERNS["python"])
    for pat, pat_name in target_patterns:
        if re.search(pat, test_content):
            action_rule = format_action_rule(VIOLATION_DUMMY_ASSERTION)
            return False, (
                f"[PreTool 차단: 더미 자해 단언문 감지]\n"
                f"테스트 파일에 무의미한 가짜 실패 코드('{pat_name}')가 감지되었습니다.\n"
                f"{action_rule}"
            )
    return True, ""


def build_test_command_spec(
    stack: str,
    test_rel_path: str,
    is_win32: bool = False,
    python_exe: str = "python"
) -> Tuple[List[str], bool]:
    """언어 스택별 단독 테스트 명령어 및 shell 옵션을 생성하는 순수 함수."""
    cmd: List[str] = []
    use_shell = False

    if stack == "node":
        use_shell = is_win32
        cmd = ["npm", "test", "--", test_rel_path]
    elif stack == "rust":
        use_shell = is_win32
        test_name = os.path.splitext(os.path.basename(test_rel_path))[0]
        cmd = ["cargo", "test", "--test", test_name]
    elif stack == "go":
        use_shell = is_win32
        dir_name = os.path.dirname(test_rel_path).replace("\\", "/").strip("./ ")
        pkg_target = f"./{dir_name}" if dir_name else "."
        cmd = ["go", "test", "-v", pkg_target]
    else:  # python
        cmd = [python_exe, "-m", "pytest", test_rel_path, "-q"]

    return cmd, use_shell


def evaluate_test_execution_result(
    stack: str,
    returncode: int,
    combined_output: str,
    test_rel_path: str
) -> Tuple[bool, str]:
    """단독 테스트 실행 결과(리턴코드, 출력 로그)를 분석하여 진짜 Red 여부를 판정하는 순수 함수."""
    # A. 테스트가 이미 100% 통과(Green)하고 있는 경우
    if returncode == 0:
        return False, (
            f"[PreTool 차단: 의도된 실패(Red) 미확인 가짜 테스트 감지]\n"
            f"작성된 핀-테스트 '{test_rel_path}'가 비즈니스 코드를 수정하기도 전에 이미 100% 통과(Green)하고 있습니다.\n"
            f"철칙: 구현 전에 반드시 실패(Red)가 발생하는 진짜 검증 테스트를 작성한 후 비즈니스 코드를 수정하세요."
        )

    # B. 언어별 가짜 Red(컴파일/모듈/임포트/문법 에러) 차단
    err_signatures = FAKE_RED_SIGNATURES.get(stack, FAKE_RED_SIGNATURES["python"])
    if (stack == "python" and returncode == 2) or any(sig in combined_output for sig in err_signatures):
        action_rule = format_action_rule(VIOLATION_SYNTAX_ERROR_RED)
        return False, (
            f"[PreTool 차단: 가짜 Red(컴파일/임포트/문법 에러) 감지]\n"
            f"테스트 파일 '{test_rel_path}' 실행 중 언어 컴파일/수집/임포트 에러가 발생했습니다.\n"
            f"{action_rule}"
        )

    # C. 비즈니스 단언 실패 (진짜 Red 승인)
    pass_signatures = REAL_RED_SIGNATURES.get(stack, REAL_RED_SIGNATURES["python"])
    if returncode != 0 and (any(sig in combined_output for sig in pass_signatures) or returncode == 1):
        return True, ""

    # D. 기타 비정상 종료 시 안전 차단
    tail_log = combined_output[-300:] if len(combined_output) > 300 else combined_output
    return False, f"[PreTool 차단: 테스트 비정상 종료 (Exit Code {returncode})]\n{tail_log}"
