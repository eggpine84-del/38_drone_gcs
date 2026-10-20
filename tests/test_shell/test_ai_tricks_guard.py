# -*- coding: utf-8 -*-
# [파일명]: test_ai_tricks_guard.py (AI 3대 치명적 꼼수 전담 AST 가드)
# [원칙] 1. 변종 에러 삼키기(..., return None) 금지 | 2. 가변 기본 인자([], {}) 금지 | 3. f-string 날쿼리 조립 금지
# [SYSTEM] Senior Staff Engineer (Google/Amazon) - Anti-Silent-Bug AST Architecture Guard.
import ast
import os
import re
import pytest

LEGACY_TRICKS_ALLOWLIST: set[str] = set()

SQL_STATEMENT_PATTERN = re.compile(
    r"\b(SELECT\s+.+\s+FROM|INSERT\s+INTO|UPDATE\s+\w+\s+SET|DELETE\s+FROM|CREATE\s+TABLE|DROP\s+TABLE)\b",
    re.IGNORECASE | re.DOTALL,
)


def _is_swallowed_exception_body(body: list[ast.stmt]) -> tuple[bool, str]:
    """except 블록이 pass, ..., 리터럴 단독 표기, 또는 return None으로 에러를 삼키는지 판정합니다."""
    if len(body) != 1:
        return False, ""
    stmt = body[0]

    # 1) except: pass
    if isinstance(stmt, ast.Pass):
        return True, "except: pass"

    # 2) except: ... (Ellipsis) 또는 의미 없는 상수/문자열 단독 배치
    if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant):
        if stmt.value.value is Ellipsis:
            return True, "except: ..."
        return True, f"except: {repr(stmt.value.value)}"

    # 3) except: return 또는 except: return None
    if isinstance(stmt, ast.Return):
        if stmt.value is None:
            return True, "except: return"
        if isinstance(stmt.value, ast.Constant) and stmt.value.value is None:
            return True, "except: return None"

    return False, ""


def _is_mutable_default(node: ast.AST) -> tuple[bool, str]:
    """함수 기본 인자가 [], {}, set() 등 가변(Mutable) 객체인지 판정합니다."""
    if isinstance(node, ast.List):
        return True, "[]"
    if isinstance(node, ast.Dict):
        return True, "{}"
    if isinstance(node, ast.Set):
        return True, "{...}"
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in ("list", "dict", "set")
    ):
        return True, f"{node.func.id}()"
    return False, ""


def _is_formatted_sql_arg(arg: ast.AST) -> tuple[bool, str]:
    """execute()의 첫 번째 인자가 f-string, .format(), %, + 로 조립된 동적 문자열인지 판정합니다."""
    if isinstance(arg, ast.JoinedStr):
        return True, "f-string (f\"...\")"
    if isinstance(arg, ast.BinOp) and isinstance(arg.op, (ast.Mod, ast.Add)):
        op_label = "'%'" if isinstance(arg.op, ast.Mod) else "'+'"
        return True, f"문자열 {op_label} 직접 결합"
    if (
        isinstance(arg, ast.Call)
        and isinstance(arg.func, ast.Attribute)
        and arg.func.attr == "format"
    ):
        return True, ".format() 문자열 조립"
    return False, ""


def test_ai_three_fatal_tricks_guard():
    """AI의 3대 치명적 꼼수(변종 에러 삼키기, 가변 기본 인자, f-string SQL 조립)를 AST로 전수 검사합니다."""
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

            if rel_path in LEGACY_TRICKS_ALLOWLIST:
                continue

            with open(fpath, "r", encoding="utf-8", errors="ignore") as fp:
                try:
                    tree = ast.parse(fp.read(), filename=f)
                except SyntaxError:
                    continue

            for node in ast.walk(tree):
                # 1. 변종 에러 삼키기 (except: pass / except: ... / except: return None) 적발
                if isinstance(node, ast.ExceptHandler):
                    is_swallowed, pattern_name = _is_swallowed_exception_body(node.body)
                    if is_swallowed:
                        violations.append(
                            f"[1. 변종 에러 삼키기 금지 위반]: {rel_path} (라인 {node.lineno}) "
                            f"-> '{pattern_name}' 감지. 예외를 침묵시키지 말고 표준 에러 봉투를 반환하거나 예외를 전파하세요."
                        )

                # 2. 함수 인자 가변 기본값 (def fn(items=[], data={})) 적발
                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    all_defaults = list(node.args.defaults) + [
                        d for d in node.args.kw_defaults if d is not None
                    ]
                    for d_node in all_defaults:
                        is_mutable, repr_str = _is_mutable_default(d_node)
                        if is_mutable:
                            violations.append(
                                f"[2. 가변 기본 인자(Mutable Default) 금지 위반]: {rel_path}:{node.name} (라인 {node.lineno}) "
                                f"-> 기본값에 '{repr_str}' 직접 사용 금지 (호출 간 데이터 섞임 사고 원인). "
                                f"기본값은 None으로 두고 함수 내부에서 초기화하세요."
                            )

                # 3-A. execute(f"SELECT ...") 직접 조립 적발
                elif (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr in ("execute", "executemany", "executescript")
                    and node.args
                ):
                    is_dynamic_sql, method_desc = _is_formatted_sql_arg(node.args[0])
                    if is_dynamic_sql:
                        violations.append(
                            f"[3. 동적 날쿼리 조립 금지 위반]: {rel_path} (라인 {node.lineno}) "
                            f"-> {node.func.attr}() 내부에 {method_desc} 감지. "
                            f"반드시 파라미터 바인딩(?, :param)을 사용하세요."
                        )

                # 3-B. sql = f"SELECT ... {id}" 형태로 변수에 먼저 담아 우회하는 f-string SQL 적발
                elif isinstance(node, ast.JoinedStr):
                    static_text = " ".join(
                        part.value for part in node.values
                        if isinstance(part, ast.Constant) and isinstance(part.value, str)
                    )
                    if SQL_STATEMENT_PATTERN.search(static_text):
                        violations.append(
                            f"[3. f-string SQL 변수 우회 금지 위반]: {rel_path} (라인 {node.lineno}) "
                            f"-> f-string 내부에 SQL 구문 직접 보간 감지. "
                            f"쿼리 문자열과 파라미터 튜플을 분리해 바인딩하세요."
                        )

    assert not violations, (
        f"\n[AI 3대 치명적 꼼수 가드 위반 감지 ({len(violations)}건)]\n"
        + "\n".join(violations)
        + "\n\n철칙: 예외 침묵(..., return None), 가변 기본 인자([], {}), f-string SQL 조립은 영구 금지됩니다."
    )
