# [파일명]: post_tool_guard_core.py | [용도] PostTool 파이썬 문법 검증 순수 코어 (Pure Functional Core)
from typing import Tuple


def format_syntax_error_message(filename: str, error_detail: str) -> str:
    """문법 오류 감지 시 AI에게 제공할 정형화된 안내 메시지를 생성하는 순수 함수."""
    return (
        f"[PostTool 경고: 방금 수정한 파일에 파이썬 문법 오류 감지!]\n"
        f"오류 파일: {filename}\n"
        f"상세 내용: {error_detail}\n"
        f"조치 요령: 다른 작업을 진행하기 전에 방금 발생한 문법 오류(괄호/들여쓰기/오타)를 즉시 바로잡으세요."
    )


def verify_python_syntax(code_str: str, filename: str = "target.py") -> Tuple[bool, str]:
    """파이썬 코드 문자열의 문법(Syntax/Indentation) 무결성을 0.001초 만에 검증하는 순수 함수."""
    try:
        compile(code_str, filename, "exec")
        return True, ""
    except (SyntaxError, IndentationError) as err:
        err_msg = f"{type(err).__name__}: {err}"
        return False, format_syntax_error_message(filename, err_msg)
    except Exception as err:
        err_msg = f"{type(err).__name__}: {err}"
        return False, format_syntax_error_message(filename, err_msg)
