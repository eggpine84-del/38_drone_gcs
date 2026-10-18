# -*- coding: utf-8 -*-
# [파일명]: pre_tool_shell.py | [용도] PreToolUse 관문 전용 디스크/설정/프로세스 I/O 쉘
import os
import sys
import json
import time
def load_guard_config(project_root: str) -> dict:
    """중앙 관제 설정 파일(.agents/guard_config.json) 로드 및 안전 폴백 제공."""
    cfg_path = os.path.join(project_root, ".agents", "guard_config.json")
    if os.path.exists(cfg_path):
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    try:
        from core.pre_tool.pre_tool_guard_core import DEFAULT_GUARD_CONFIG
        return DEFAULT_GUARD_CONFIG
    except Exception:
        return {}


def check_and_consume_deploy_token(project_root: str) -> bool:
    """1회용 배포 승인 마패 토큰(.deploy_token) 확인 및 즉시 자동 자폭(소멸)."""
    token_path = os.path.join(project_root, ".agents", ".deploy_token")
    if os.path.exists(token_path):
        try:
            os.remove(token_path)
            return True
        except Exception:
            pass
    return False


def safe_read_stdin(max_wait_sec: float = 0.1, interval_sec: float = 0.005) -> dict:
    """Windows/Linux 파이프 무한 블로킹을 회피하며 청크 분할 도착 시에도 JSON이 완성될 때까지 누적 수신하는 방탄 I/O 함수."""
    start_time = time.time()
    buffer = ""
    try:
        if sys.platform == "win32":
            import msvcrt
            import ctypes
            handle = msvcrt.get_osfhandle(sys.stdin.fileno())
            avail = ctypes.c_ulong(0)
            while time.time() - start_time <= max_wait_sec:
                res = ctypes.windll.kernel32.PeekNamedPipe(handle, None, 0, None, ctypes.byref(avail), None)
                if res and avail.value > 0:
                    chunk = sys.stdin.read(avail.value)
                    if chunk:
                        buffer += chunk
                        try:
                            return json.loads(buffer)
                        except json.JSONDecodeError:
                            pass  # 청크 분할 도착 상태 ➔ 다음 청크 대기
                time.sleep(interval_sec)
            if buffer.strip():
                try:
                    return json.loads(buffer)
                except Exception:
                    return {}
            return {}
        else:
            import select
            remaining = max_wait_sec
            while remaining > 0:
                rlist, _, _ = select.select([sys.stdin], [], [], min(remaining, interval_sec))
                if rlist:
                    chunk = sys.stdin.read()
                    if chunk:
                        buffer += chunk
                        try:
                            return json.loads(buffer)
                        except json.JSONDecodeError:
                            pass
                remaining = max_wait_sec - (time.time() - start_time)
            if buffer.strip():
                try:
                    return json.loads(buffer)
                except Exception:
                    return {}
            return {}
    except Exception:
        return {}


