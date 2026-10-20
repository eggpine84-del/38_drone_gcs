# -*- coding: utf-8 -*-
# [파일명]: test_no_if_guard.py (Table-Driven Flat & Anti-Spaghetti 아키텍처 가드)
# [원칙] 1. elif 체인 영구 금지 | 2. 직·간접 중첩 if 금지 | 3. 중첩 삼항연산자 금지 | 4. 에러 삼키기 금지
import ast
import os
import pytest

LEGACY_ALLOWLIST = set()


def _has_descendant_if(statements: list[ast.stmt]) -> bool:
    """문장 리스트 내부(for/with/try 블록 안쪽 포함)에 하위 if문이 존재하는지 재귀 탐색"""
    for stmt in statements:
        for child in ast.walk(stmt):
            if isinstance(child, ast.If):
                return True
    return False


def test_no_spaghetti_if_architecture_guard():
    """모든 모듈에서 스파게티 분기(elif, 중첩 if, 중첩 삼항연산자)와 에러 삼키기를 기계적으로 차단합니다."""
    src_root = "src"
    if not os.path.exists(src_root):
        pytest.skip("src 디렉터리 미도입 프로젝트 스킵")

    violations = []

    for root, _, files in os.walk(src_root):
        for f in files:
            if not f.endswith(".py"):
                continue
            fpath = os.path.join(root, f)
            rel_path = os.path.relpath(fpath).replace("\\", "/")

            if rel_path in LEGACY_ALLOWLIST:
                continue

            with open(fpath, "r", encoding="utf-8", errors="ignore") as fp:
                try:
                    tree = ast.parse(fp.read(), filename=f)
                except SyntaxError:
                    continue

                for node in ast.walk(tree):
                    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        continue

                    for sub in ast.walk(node):
                        # 1. if / elif / 중첩 if 검사
                        if isinstance(sub, ast.If):
                            is_elif = (
                                sub.orelse
                                and len(sub.orelse) == 1
                                and isinstance(sub.orelse[0], ast.If)
                            )
                            if is_elif:
                                violations.append(
                                    f"[elif 분기 체인 금지]: {rel_path}:{node.name} (라인 {sub.lineno}) "
                                    f"-> 'elif' 발견. Table-Driven Dispatch(딕셔너리 매핑)로 평탄화하세요."
                                )

                            # body 내부(with/for/try 안쪽 포함)에 또 다른 if가 있는지 검사
                            if _has_descendant_if(sub.body):
                                violations.append(
                                    f"[중첩 if문 금지]: {rel_path}:{node.name} (라인 {sub.lineno}) "
                                    f"-> if 블록 내부에 하위 if문 감지. 조기 가드절(Early Return)로 분리하세요."
                                )

                            # elif가 아닌 일반 else 블록 내부에 숨긴 if 검사
                            if not is_elif and _has_descendant_if(sub.orelse):
                                violations.append(
                                    f"[else 내부 중첩 if 금지]: {rel_path}:{node.name} (라인 {sub.lineno}) "
                                    f"-> else 블록 내부에 하위 if문 감지. 가드절 또는 테이블 매핑으로 분리하세요."
                                )

                        # 2. 삼항 연산자(a if cond else b) 중첩 꼼수 차단
                        elif isinstance(sub, ast.IfExp):
                            if isinstance(sub.body, ast.IfExp) or isinstance(sub.orelse, ast.IfExp):
                                violations.append(
                                    f"[중첩 삼항연산자 꼼수 금지]: {rel_path}:{node.name} (라인 {sub.lineno}) "
                                    f"-> 인라인 if-else 체인 감지. 딕셔너리 매핑(dict.get)으로 교체하세요."
                                )

                        # 3. 에러 삼키기 (except: pass / except Exception: pass) 차단
                        elif isinstance(sub, ast.ExceptHandler):
                            if len(sub.body) == 1 and isinstance(sub.body[0], (ast.Pass, ast.Constant)):
                                violations.append(
                                    f"[에러 삼키기(Error Swallowing) 금지]: {rel_path}:{node.name} (라인 {sub.lineno}) "
                                    f"-> 무책임한 except: pass 감지. 명시적 에러 봉투를 반환하거나 예외를 전파하세요."
                                )

    assert not violations, (
        f"[Table-Driven Flat 아키텍처 헌법 위반 감지 ({len(violations)}건)]\n"
        + "\n".join(violations) + "\n\n"
        + "철칙: 모든 다중 분기는 Table-Driven Dispatch(딕셔너리 매핑)와 단발 Early Return으로만 작성하세요."
    )