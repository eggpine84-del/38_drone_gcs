# -*- coding: utf-8 -*-
# [파일명]: common_shell.py | [용도] 시스템 stdin/stdout 및 공통 I/O 쉘 어댑터
import sys
import json

if hasattr(sys.stdin, "reconfigure"):
    sys.stdin.reconfigure(encoding="utf-8")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


from shell.pre_tool.pre_tool_shell import safe_read_stdin



def send_response(decision: str, reason: str = "") -> None:
    """Antigravity IDE 훅 응답을 stdout JSON으로 송신하고 즉시 정상 종료."""
    payload = {"decision": decision}
    if reason:
        payload["reason"] = reason
    print(json.dumps(payload, ensure_ascii=False))
    sys.exit(0)
