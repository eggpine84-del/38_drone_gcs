# -*- coding: utf-8 -*-
# [파일명]: test_no_if_guard.py (Table-Driven Flat 아키텍처 가드)
# [원칙] 1. elif 분기 체인 영구 금지 | 2. 중첩 if(Nested If) 금지 | 3. Table-Driven Dispatch 강제
# [SYSTEM] Senior Staff Engineer (Google/Amazon) - Anti-Spaghetti AST Architecture Guard.
import ast
import os
import pytest

# 분기형 if문 허용 예외 파일 (점진적 리팩토링용 화이트리스트)
LEGACY_ALLOWLIST = set()


def test_no_spaghetti_if_architecture_guard():
    """모든 함수에서 elif 분기 체인 및 중첩 if문을 기계적으로 차단하고 Table-Driven을 강제합니다."""
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
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        # 1. 함수 직속 및 하위 if 노드 수집
                        if_nodes = [n for n in ast.walk(node) if isinstance(n, ast.If)]
                        if not if_nodes:
                            continue

                        # 2. elif 분기 체인 검출 (if의 orelse에 또 if가 연결된 스파게티)
                        for if_n in if_nodes:
                            if if_n.orelse and len(if_n.orelse) == 1 and isinstance(if_n.orelse[0], ast.If):
                                violations.append(
                                    f"[elif 분기 체인 금지 위반]: {rel_path}:{node.name} (라인 {if_n.lineno}) "
                                    f"-> 'elif' 발견. Table-Driven Dispatch(딕셔너리 매핑)로 리팩토링하세요."
                                )

                        # 3. 중첩 if (Nested If) 검출 (if 블록 내부에 또 다른 if문이 있는 들여쓰기 스파게티)
                        for if_n in if_nodes:
                            nested_ifs = [n for n in if_n.body if isinstance(n, ast.If)]
                            if nested_ifs:
                                violations.append(
                                    f"[중첩 if문(Nested If) 금지 위반]: {rel_path}:{node.name} (라인 {if_n.lineno}) "
                                    f"-> if문 내부에 또 다른 if문 감지. 단발 조기 가드절(Early Return)로 분리하세요."
                                )

    assert not violations, (
        f"[Table-Driven Flat 아키텍처 헌법 위반: if문 스파게티 감지 ({len(violations)}건)]\n"
        + "\n".join(violations) + "\n\n"
        + "철칙: 3개 이상의 분기는 무조건 Table-Driven Dispatch(딕셔너리 매핑)로 평평하게(Flat) 구현하세요."
    )
