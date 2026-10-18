# [파일명]: post_tool_guard.py | [용도] PostToolUse 파일 수정 직후 0.01초 초고속 문법/오타 자동 감찰관
import sys
import os
import json
import py_compile

# 표준 입출력 UTF-8 강제
if hasattr(sys.stdin, "reconfigure"):
    sys.stdin.reconfigure(encoding='utf-8')
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding='utf-8')


# Core 순수 검증 로직 임포트 및 Facade 재노출 (하위 호환성 100% 유지)
cur_script_dir = os.path.dirname(os.path.abspath(__file__))
if cur_script_dir not in sys.path:
    sys.path.insert(0, cur_script_dir)

try:
    from core.post_tool.post_tool_guard_core import verify_python_syntax, format_syntax_error_message
except ImportError:
    from .core.post_tool.post_tool_guard_core import verify_python_syntax, format_syntax_error_message


def send_response(decision: str, reason: str = ""):
    """결정론적 응답 반환 및 종료."""
    payload = {"decision": decision}
    if reason:
        payload["reason"] = reason
    print(json.dumps(payload, ensure_ascii=False))
    sys.exit(0)


def safe_read_stdin(max_wait_sec: float = 0.1, interval_sec: float = 0.005) -> dict:
    """Windows/Linux 파이프 무한 블로킹을 회피하며 최대 0.1초 동안 안전하게 버퍼를 수신하는 함수."""
    import time
    start_time = time.time()
    try:
        if sys.platform == "win32":
            import msvcrt
            import ctypes
            handle = msvcrt.get_osfhandle(sys.stdin.fileno())
            avail = ctypes.c_ulong(0)
            while time.time() - start_time <= max_wait_sec:
                res = ctypes.windll.kernel32.PeekNamedPipe(handle, None, 0, None, ctypes.byref(avail), None)
                if res and avail.value > 0:
                    raw_input = sys.stdin.read(avail.value)
                    return json.loads(raw_input) if raw_input.strip() else {}
                time.sleep(interval_sec)
            return {}
        else:
            import select
            remaining = max_wait_sec
            while remaining > 0:
                rlist, _, _ = select.select([sys.stdin], [], [], min(remaining, interval_sec))
                if rlist:
                    raw_input = sys.stdin.read()
                    return json.loads(raw_input) if raw_input.strip() else {}
                remaining = max_wait_sec - (time.time() - start_time)
            return {}
    except Exception:
        return {}


def main():
    payload = safe_read_stdin()

    tool_call = payload.get("toolCall", {})
    args = tool_call.get("args", {})

    target_file = args.get("TargetFile", "")
    if not target_file:
        send_response("allow")

    # 대상 파일 경로 확인
    target_abs = os.path.abspath(target_file)
    if not os.path.exists(target_abs):
        send_response("allow")

    # 파이썬(.py) 파일인 경우 0.01초 초고속 문법 컴파일 검증 (Pure Core 위임)
    if target_abs.endswith(".py"):
        try:
            with open(target_abs, "r", encoding="utf-8", errors="replace") as f:
                code_content = f.read()
            is_valid, reason = verify_python_syntax(code_content, os.path.basename(target_abs))
            if not is_valid:
                send_response("deny", reason)
            send_response("allow")
        except Exception:
            send_response("allow")

    # 기타 파일은 즉시 통과
    send_response("allow")


if __name__ == "__main__":
    main()
