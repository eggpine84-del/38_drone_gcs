# [파일명]: syntax_guard_core.py | [용도] PreTool 파이썬 문법 사전 감찰 순수 코어 (Pure Functional Core)
import ast
from typing import Any, Dict, Tuple


def simulate_patched_code(current_code: str, tool_name: str, args: Dict[str, Any]) -> str:
    """도구 호출 인자를 기반으로 메모리 상에서 가상 패치된 최종 코드 문자열을 합성하는 순수 함수."""
    if tool_name == "write_to_file":
        return str(args.get("CodeContent", ""))

    if tool_name == "replace_file_content":
        target = args.get("TargetContent", "")
        replacement = args.get("ReplacementContent", "")
        allow_multiple = bool(args.get("AllowMultiple", False))
        if not target or target not in current_code:
            return current_code
        if allow_multiple:
            return current_code.replace(target, replacement)
        return current_code.replace(target, replacement, 1)

    if tool_name == "multi_replace_file_content":
        chunks = args.get("ReplacementChunks", [])
        patched = current_code
        for chunk in chunks:
            t = chunk.get("TargetContent", "")
            r = chunk.get("ReplacementContent", "")
            m = bool(chunk.get("AllowMultiple", False))
            if t and t in patched:
                patched = patched.replace(t, r) if m else patched.replace(t, r, 1)
        return patched

    return current_code


def check_python_syntax_pre_tool(
    norm_rel_path: str,
    tool_name: str,
    args: Dict[str, Any],
    current_file_content: str = "",
    enable_check: bool = True
) -> Tuple[bool, str]:
    """PreToolUse 시점에 대상 파이썬 파일의 문법 오타를 0.001초 만에 사전 판정하는 순수 함수."""
    if not enable_check:
        return True, ""

    norm = norm_rel_path.replace("\\", "/").lower()
    if not norm.endswith(".py"):
        return True, ""

    simulated_code = simulate_patched_code(current_file_content, tool_name, args)
    if not simulated_code:
        return True, ""

    try:
        ast.parse(simulated_code, filename=norm_rel_path)
        return True, ""
    except (SyntaxError, IndentationError) as err:
        line = getattr(err, "lineno", "?")
        col = getattr(err, "offset", "?")
        msg = getattr(err, "msg", str(err))
        reason = (
            f"[PreTool 차단: 파이썬 문법/오타 감지]\n"
            f"대상 파일: {norm_rel_path}:{line}:{col}\n"
            f"오류 상세: {type(err).__name__}: {msg}\n"
            f"조치 요령: 디스크 오염을 방지하기 위해 파일 수정을 사전에 차단했습니다. 오타/들여쓰기를 수리한 후 다시 호출하세요."
        )
        return False, reason
    except Exception as err:
        reason = (
            f"[PreTool 차단: 파이썬 문법/오타 감지]\n"
            f"대상 파일: {norm_rel_path}\n"
            f"오류 상세: {type(err).__name__}: {err}\n"
            f"조치 요령: 디스크 오염을 방지하기 위해 파일 수정을 사전에 차단했습니다. 오타/들여쓰기를 수리한 후 다시 호출하세요."
        )
        return False, reason
