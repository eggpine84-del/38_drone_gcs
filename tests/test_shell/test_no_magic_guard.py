# -*- coding: utf-8 -*-
# [파일명]: test_no_magic_guard.py (침묵 매직넘버 폴백 영구 차단 가드)
# [원칙] G5. Zero Magic Fallback (상수 선언 없는 인라인 가짜 기본값 날조 영구 금지)
# [SYSTEM] Senior Staff Engineer (Google/Amazon) - Anti-Silent Fallback Guard.
import ast
import os
import pytest

SAFE_NUMBERS: frozenset[int | float] = frozenset({0, 0.0, 1, -1})
# 인프라 설정(config.py) 및 마이그레이션 등 합법적 환경변수 기본값 허용 파일
CONFIG_ALLOWLIST_PATTERNS: tuple[str, ...] = ("config.py", "settings.py", "conf.py")
LEGACY_MAGIC_ALLOWLIST: set[str] = set()


def _extract_numeric_literal(node: ast.AST) -> int | float | None:
    """AST 노드에서 숫자 리터럴(음수 UnaryOp 포함)을 추출합니다. 숫자가 아니면 None 반환."""
    if isinstance(node, ast.Constant) and type(node.value) in (int, float):
        return node.value
    if (
        isinstance(node, ast.UnaryOp)
        and isinstance(node.op, (ast.USub, ast.UAdd))
        and isinstance(node.operand, ast.Constant)
        and type(node.operand.value) in (int, float)
    ):
        return -node.operand.value if isinstance(node.op, ast.USub) else node.operand.value
    return None


def _is_magic_number(node: ast.AST) -> tuple[bool, int | float | None]:
    """허용된 기본값(0, 1, -1)이 아닌 비즈니스 매직넘버인지 판정합니다."""
    num = _extract_numeric_literal(node)
    if num is not None and num not in SAFE_NUMBERS:
        return True, num
    return False, None


def test_no_silent_magic_number_fallback_guard():
    """삼항연산자(else 50), dict.get/getattr 기본값, 단락평가(or 50)의 가짜 매직넘버 폴백을 차단합니다."""
    src_root = "src"
    if not os.path.exists(src_root):
        pytest.skip("src 디렉터리 미도입 프로젝트 스킵")

    violations = []

    for root, _, files in os.walk(src_root):
        for f in files:
            if not f.endswith(".py"):
                continue
            # 환경설정 파일은 os.getenv 기본값 등 인프라 설정용 예외 인정
            if f in CONFIG_ALLOWLIST_PATTERNS:
                continue

            fpath = os.path.join(root, f)
            rel_path = os.path.relpath(fpath).replace("\\", "/")
            if rel_path in LEGACY_MAGIC_ALLOWLIST:
                continue

            with open(fpath, "r", encoding="utf-8", errors="ignore") as fp:
                try:
                    tree = ast.parse(fp.read(), filename=f)
                except SyntaxError:
                    continue

            for node in ast.walk(tree):
                # 1. 삼항 연산자 폴백: a if cond else 50 (또는 50 if cond else a)
                if isinstance(node, ast.IfExp):
                    for branch, label in ((node.orelse, "else"), (node.body, "if")):
                        is_magic, val = _is_magic_number(branch)
                        if is_magic:
                            violations.append(
                                f"[삼항연산자 매직넘버 날조 적발] {rel_path} (라인 {node.lineno}): "
                                f"'{label} {val}' -> 인라인 가짜 숫자 금지. 파일 상단 대문자 상수로 선언하거나 Fail-Fast 예외를 던지세요."
                            )

                # 2. dict.get("k", 50) 및 getattr(obj, "k", 50) 기본값 땜질
                elif isinstance(node, ast.Call):
                    # obj.get("key", 50)
                    if (
                        isinstance(node.func, ast.Attribute)
                        and node.func.attr in ("get", "setdefault")
                        and len(node.args) >= 2
                    ):
                        is_magic, val = _is_magic_number(node.args[1])
                        if is_magic:
                            violations.append(
                                f"[{node.func.attr}() 매직넘버 폴백 적발] {rel_path} (라인 {node.lineno}): "
                                f"기본값 '{val}' 금지 -> 누락된 데이터에 임의 숫자를 채우지 말고 상수로 선언하거나 거절(Fail-Fast)하세요."
                            )
                    # getattr(obj, "key", 50)
                    elif (
                        isinstance(node.func, ast.Name)
                        and node.func.id == "getattr"
                        and len(node.args) >= 3
                    ):
                        is_magic, val = _is_magic_number(node.args[2])
                        if is_magic:
                            violations.append(
                                f"[getattr() 매직넘버 폴백 적발] {rel_path} (라인 {node.lineno}): "
                                f"기본값 '{val}' 금지 -> 명시적 상수 또는 스키마 필드를 사용하세요."
                            )

                # 3. 단락 평가 폴백: val or 50
                elif isinstance(node, ast.BoolOp) and isinstance(node.op, ast.Or):
                    for v_node in node.values[1:]:
                        is_magic, val = _is_magic_number(v_node)
                        if is_magic:
                            violations.append(
                                f"[or 단락평가 매직넘버 폴백 적발] {rel_path} (라인 {node.lineno}): "
                                f"'or {val}' 금지 -> None/빈값일 때 가짜 숫자로 땜질하지 마세요."
                            )

    assert not violations, (
        f"\n[G5 헌법 위반: 침묵 매직넘버 폴백(Silent Magic Fallback) 감지 ({len(violations)}건)]\n"
        + "\n".join(violations)
        + "\n\n철칙: 근거 없는 인라인 숫자로 에러를 덮지 마세요. 반드시 대문자 상수(예: DEFAULT_TIMEOUT = 30)로 명명하거나 즉시 에러를 반환하세요."
    )
