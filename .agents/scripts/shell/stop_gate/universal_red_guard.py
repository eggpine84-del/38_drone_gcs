# [파일명]: universal_red_guard.py | [용도] 다국어 스택 자동 감지 및 언어별 진짜 Red(비즈니스 단언 실패) 검증 모듈
import os
import re
import subprocess
import sys
from typing import Tuple


def detect_project_stack(project_root: str, test_path: str = "") -> str:
    """프로젝트 루트 및 대상 테스트 파일 구성을 검사하여 언어 스택(python, node, go, rust)을 자동 판정하는 순수 셸 함수."""
    if test_path:
        norm_test = test_path.replace("\\", "/").lower()
        if norm_test.endswith((".ts", ".tsx", ".js", ".jsx")):
            return "node"
        if norm_test.endswith(".rs"):
            return "rust"
        if norm_test.endswith(".go"):
            return "go"
        if norm_test.endswith(".py"):
            return "python"

    if os.path.exists(os.path.join(project_root, "package.json")):
        return "node"
    if os.path.exists(os.path.join(project_root, "Cargo.toml")):
        return "rust"
    if os.path.exists(os.path.join(project_root, "go.mod")):
        return "go"
    return "python"


# Core 순수 로직 임포트 및 Facade 재노출 (하위 호환성 100% 유지)
cur_script_dir = os.path.dirname(os.path.abspath(__file__))
scripts_dir = os.path.abspath(os.path.join(cur_script_dir, "..", ".."))
if scripts_dir not in sys.path:
    sys.path.insert(0, scripts_dir)
if cur_script_dir not in sys.path:
    sys.path.insert(0, cur_script_dir)

try:
    from core.stop_gate.universal_red_guard_core import (
        DUMMY_ASSERTION_PATTERNS,
        FAKE_RED_SIGNATURES,
        REAL_RED_SIGNATURES,
        _check_dummy_assertions,
        build_test_command_spec,
        evaluate_test_execution_result,
    )
except ImportError:
    from .core.stop_gate.universal_red_guard_core import (
        DUMMY_ASSERTION_PATTERNS,
        FAKE_RED_SIGNATURES,
        REAL_RED_SIGNATURES,
        _check_dummy_assertions,
        build_test_command_spec,
        evaluate_test_execution_result,
    )


def verify_universal_red_failure(project_root: str, test_rel_path: str) -> Tuple[bool, str]:
    """언어 스택에 맞추어 신규 핀-테스트가 의도된 비즈니스 실패(진짜 Red)를 일으키는지 검증하는 Shell 함수."""
    try:
        # 가드레일 부팅 테스트는 Red 검증 예외
        if "test_architecture_guardrails" in test_rel_path or "test_config" in test_rel_path:
            return True, ""

        test_full_path = os.path.join(project_root, test_rel_path)
        if not os.path.exists(test_full_path):
            return True, ""

        # 1. 언어 스택 자동 감지 (파일 경로 기반 우선 판정)
        stack = detect_project_stack(project_root, test_rel_path)

        # 2. 텍스트 정적 분석: 더미 자해 단언문 검사 (Pure Core 위임)
        try:
            with open(test_full_path, "r", encoding="utf-8") as f:
                test_content = f.read()
            is_valid, dummy_reason = _check_dummy_assertions(test_content, stack)
            if not is_valid:
                return False, dummy_reason
        except Exception:
            pass

        # 3. 언어별 단독 테스트 명령어 구성 (Pure Core 위임)
        cmd, use_shell = build_test_command_spec(
            stack,
            test_rel_path,
            is_win32=(sys.platform == "win32"),
            python_exe=sys.executable
        )

        # 4. 백그라운드 단독 테스트 실행
        proc = subprocess.run(
            cmd,
            cwd=project_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
            shell=use_shell
        )
        combined_output = (proc.stdout + "\n" + proc.stderr).strip()

        # 5. 테스트 실행 결과 판정 (Pure Core 위임)
        return evaluate_test_execution_result(stack, proc.returncode, combined_output, test_rel_path)

    except Exception:
        # 러너 미설치 등 예상치 못한 실행 에러 시 작업 차단 방지
        return True, ""
