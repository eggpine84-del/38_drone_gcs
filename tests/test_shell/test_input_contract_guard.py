# -*- coding: utf-8 -*-
# [파일명]: test_input_contract_guard.py (대문 입력 규격 및 3대 핀테스트 완제품 가드)
# [원칙] G1 입력 규격 강제: 날것의 dict 대문 유입 영구 금지, extra='forbid' 화이트리스트 필수
# [SYSTEM] Senior Staff Engineer (Google/Amazon) - Boundary Contract & Pin-Test Guard.
#
# [3대 핀테스트 표준 패턴 안내] (가드 아님, 피처별 tests/test_features/{feature}/test_pin_*.py에 직접 작성)
#  1. 화이트리스트: 미정의 키 주입 시 400/422 거부를 응답 전체 대조로 단언
#  2. Fail-Fast: 증빙 누락 등 비정상 입력 시 가짜 기본값 없이 거절/동결 판정을 단언
#  3. Core 순수성: 동일 입력 2회 호출 결과 전체 객체 동일성 단언 (외부 I/O 없이)
import ast
import os
import pytest

FORBID_VALUE: str = "forbid"


def _is_forbid_literal(node: ast.AST) -> bool:
    """AST 노드가 문자열 리터럴 'forbid'인지 판정합니다."""
    return isinstance(node, ast.Constant) and node.value == FORBID_VALUE


def _config_value_forbids(value: ast.AST) -> bool:
    """model_config 할당값(ConfigDict(...) 호출 또는 dict 리터럴)에 extra='forbid'가 있는지 판정합니다."""
    if isinstance(value, ast.Call):
        return any(kw.arg == "extra" and _is_forbid_literal(kw.value) for kw in value.keywords)
    if isinstance(value, ast.Dict):
        return any(
            isinstance(k, ast.Constant) and k.value == "extra" and _is_forbid_literal(v)
            for k, v in zip(value.keys, value.values)
        )
    return False


def _class_declares_extra_forbid(node: ast.ClassDef) -> bool:
    """클래스가 실제 설정으로 extra='forbid'를 선언했는지 판정합니다 (주석/문자열 우회 불가).

    인정 형태: model_config = ConfigDict(extra=...), model_config = {"extra": ...},
    class X(BaseModel, extra=...), 내부 class Config: extra = ... (Pydantic v1)
    """
    if any(kw.arg == "extra" and _is_forbid_literal(kw.value) for kw in node.keywords):
        return True
    for stmt in node.body:
        if isinstance(stmt, (ast.Assign, ast.AnnAssign)):
            targets = stmt.targets if isinstance(stmt, ast.Assign) else [stmt.target]
            is_model_config = any(isinstance(t, ast.Name) and t.id == "model_config" for t in targets)
            if is_model_config and stmt.value is not None and _config_value_forbids(stmt.value):
                return True
        if isinstance(stmt, ast.ClassDef) and stmt.name == "Config":
            for inner in stmt.body:
                if (
                    isinstance(inner, ast.Assign)
                    and any(isinstance(t, ast.Name) and t.id == "extra" for t in inner.targets)
                    and _is_forbid_literal(inner.value)
                ):
                    return True
    return False


def test_routes_reject_raw_dict_input_guard():
    """대문 규격 가드 1: routes.py의 POST/PUT 엔드포인트 파라미터에 날것의 dict/Dict/Any 사용 차단."""
    src_root = "src"
    if not os.path.exists(src_root):
        pytest.skip("src 디렉터리 미도입 프로젝트 통과")

    violations = []
    for root, _, files in os.walk(src_root):
        for f in files:
            if not (f.endswith("routes.py") or f.endswith("route.py")):
                continue
            fpath = os.path.join(root, f)
            with open(fpath, "r", encoding="utf-8", errors="ignore") as fp:
                try:
                    tree = ast.parse(fp.read(), filename=f)
                except SyntaxError:
                    continue

                for node in ast.walk(tree):
                    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        continue

                    # 라우터 데코레이터 검사 (@router.post, @router.put, @app.post 등)
                    is_http_entry = False
                    for dec in node.decorator_list:
                        dec_repr = ""
                        if isinstance(dec, ast.Call):
                            if isinstance(dec.func, ast.Attribute):
                                dec_repr = dec.func.attr
                        elif isinstance(dec, ast.Attribute):
                            dec_repr = dec.attr
                        if dec_repr.lower() in ("post", "put", "patch"):
                            is_http_entry = True
                            break

                    if not is_http_entry:
                        continue

                    # 함수 인자 어노테이션 검사
                    for arg in node.args.args:
                        if arg.arg in ("self", "cls", "request"):
                            continue
                        ann = arg.annotation
                        if ann is None:
                            continue

                        # dict, Dict, Any 직격 감지
                        type_name = ""
                        if isinstance(ann, ast.Name):
                            type_name = ann.id
                        elif isinstance(ann, ast.Subscript) and isinstance(ann.value, ast.Name):
                            type_name = ann.value.id

                        if type_name in ("dict", "Dict", "Any"):
                            violations.append(
                                f"[{os.path.relpath(fpath)}:{node.name}]: 인자 '{arg.arg}: {type_name}' "
                                f"-> 날것의 딕셔너리 사용 금지. Pydantic DTO로 규격화 필수."
                            )

    assert not violations, (
        f"\n[아키텍처 헌법 위반: 대문 입력 규격(G1) 미준수 감지]\n"
        + "\n".join(violations)
        + "\n=> 모든 외부 입력은 'extra=\"forbid\"'가 적용된 Pydantic DTO 클래스로 바인딩해야 합니다.\n"
    )


def test_dto_extra_forbid_configuration_guard():
    """대문 규격 가드 2: DTO 클래스 정의 시 미정의 키 거부(extra='forbid') 설정 필수화 검증."""
    src_root = "src"
    if not os.path.exists(src_root):
        pytest.skip("src 디렉터리 미도입 프로젝트 통과")

    dto_files = []
    for root, _, files in os.walk(src_root):
        for f in files:
            if f.endswith(".py"):
                dto_files.append(os.path.join(root, f))

    violations = []
    for fpath in dto_files:
        with open(fpath, "r", encoding="utf-8", errors="ignore") as fp:
            content = fp.read()
            if "BaseModel" not in content:
                continue
            try:
                tree = ast.parse(content, filename=fpath)
            except SyntaxError:
                continue

            for node in ast.walk(tree):
                if not isinstance(node, ast.ClassDef):
                    continue

                # BaseModel 상속 여부 확인
                inherits_basemodel = False
                for b in node.bases:
                    if (isinstance(b, ast.Name) and b.id == "BaseModel") or (
                        isinstance(b, ast.Attribute) and b.attr == "BaseModel"
                    ):
                        inherits_basemodel = True
                        break

                if not inherits_basemodel:
                    continue

                # 실제 설정값 해석으로 extra='forbid' 선언 여부 확인 (주석/문자열 우회 차단)
                if not _class_declares_extra_forbid(node):
                    violations.append(
                        f"[{os.path.relpath(fpath)}: class {node.name}]: "
                        f"'extra=\"forbid\"' 설정 누락. 미정의 키 침묵 유입 방지를 위해 화이트리스트 설정 필수."
                    )

    assert not violations, (
        f"\n[아키텍처 헌법 위반: DTO 화이트리스트 설정 누락 감지]\n"
        + "\n".join(violations)
        + "\n=> 모든 DTO는 model_config = ConfigDict(extra=\"forbid\") 또는 model_config = {\"extra\": \"forbid\"}를 선언해야 합니다.\n"
    )

