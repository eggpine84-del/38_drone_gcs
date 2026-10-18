# [파일명]: ui_stack_guard_core.py | [용도] 4대 웹 스택(FastAPI/Jinja2/HTMX/Tailwind) 역할 침범 감찰 순수 코어
import os
from typing import Any, Dict, Tuple


DEFAULT_UI_STACK_POLICY: Dict[str, Any] = {
    "banned_frontend_patterns": [
        "fetch(",
        ".innerHTML",
        "axios.",
        ".insertAdjacentHTML"
    ],
    "banned_backend_patterns": [
        "<table",
        "<tr",
        "<td",
        "<div",
        "<span",
        "<form"
    ],
    "banned_extensions": [
        ".js",
        ".jsx",
        ".ts",
        ".tsx"
    ],
    "target_dirs": [
        "src"
    ]
}


def check_ui_stack_violation(
    target_rel_path: str,
    code_content: str,
    guard_config: Dict[str, Any]
) -> Tuple[bool, str]:
    """PreTool 파일 쓰기 직전 4대 웹 스택 상호 역할 침범 여부를 판정하는 순수 함수."""
    cfg = guard_config or {}
    switches = cfg.get("switches", {})
    if not switches.get("enforce_ui_stack_guard", False):
        return True, ""

    if not target_rel_path:
        return True, ""

    norm_path = target_rel_path.replace("\\", "/").strip('"\' ')
    _, ext = os.path.splitext(norm_path)
    ext_lower = ext.lower()

    # 문서 및 정적 바이패스 확장자 스마트 패스
    bypass_exts = set(cfg.get("bypass_extensions", [".md", ".canvas", ".txt", ".png", ".jpg", ".jpeg", ".svg", ".ico", ".log", ".json"]))
    if ext_lower in bypass_exts:
        return True, ""

    policy = cfg.get("ui_stack_policy", DEFAULT_UI_STACK_POLICY)
    target_dirs = policy.get("target_dirs", ["src"])

    # 감찰 대상 디렉터리(src/ 등) 판별
    is_in_target = any(
        norm_path.startswith(d.strip("/\\") + "/") or norm_path == d.strip("/\\")
        for d in target_dirs
    )
    if not is_in_target:
        return True, ""

    # 1. 확장자 검문 (JS/TS 파일 생성 원천 차단)
    banned_exts = set(policy.get("banned_extensions", DEFAULT_UI_STACK_POLICY["banned_extensions"]))
    if ext_lower in banned_exts:
        reason = (
            f"[PreTool 차단: UI 스택 위반 - 자바스크립트/타입스크립트 파일 생성 금지]\n"
            f"대상 파일: '{norm_path}'\n"
            "사유: 현재 프로젝트는 FastAPI + Jinja2 + HTMX 단일 파이썬 스택입니다.\n"
            "조치 요령: JS 파일 작성 대신 Jinja2 템플릿과 HTMX(hx-*) 속성으로 구현하세요."
        )
        return False, reason

    content = code_content or ""
    if not content:
        return True, ""

    # 2. 백엔드 검문 (FastAPI 파이썬 파일 내 HTML 원시 태그 하드코딩 침범 차단)
    if ext_lower == ".py":
        banned_backend = policy.get("banned_backend_patterns", DEFAULT_UI_STACK_POLICY["banned_backend_patterns"])
        for tag in banned_backend:
            if tag in content:
                reason = (
                    f"[PreTool 차단: UI 스택 위반 - 원시 태그({tag}) 하드코딩 금지]\n"
                    f"대상 파일: '{norm_path}'\n"
                    "사유: FastAPI 백엔드 코드 내부에서 HTML 태그를 문자열로 직접 조립하는 것은 Jinja2 영역 침범입니다.\n"
                    "조치 요령: 파이썬 코드 내 HTML 조립을 중단하고 Jinja2 템플릿(templates/*.html)으로 분리한 뒤 TemplateResponse로 렌더링하세요."
                )
                return False, reason

    # 3. 프론트엔드 검문 (HTML 템플릿 내 JS 수동 fetch/innerHTML 조작 차단)
    if ext_lower in [".html", ".jinja", ".jinja2"]:
        banned_frontend = policy.get("banned_frontend_patterns", DEFAULT_UI_STACK_POLICY["banned_frontend_patterns"])
        for pat in banned_frontend:
            if pat in content:
                reason = (
                    f"[PreTool 차단: UI 스택 위반 - 수동 {pat} 호출 금지]\n"
                    f"대상 파일: '{norm_path}'\n"
                    "사유: 자바스크립트 수동 DOM 조작 및 비동기 호출은 HTMX/Jinja2 영역 침범입니다.\n"
                    "조치 요령: 자바스크립트 대신 HTMX 선언적 태그 속성(hx-post, hx-target, hx-swap 등)을 사용하여 0줄 JS를 유지하세요."
                )
                return False, reason

    return True, ""
