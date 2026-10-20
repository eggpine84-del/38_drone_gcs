# -*- coding: utf-8 -*-
# [파일명]: test_ui_contract_guard.py (대장 템플릿 - 백엔드 및 HTMX 통신 계약 헌법 가드)
# [원칙] 1. 파이썬 HTML 하드코딩 금지(Jinja2 전담) | 2. HTMX 조각(Fragment) 200 계약 | 3. 300줄 이하 엄수
# [SYSTEM] Senior Staff Engineer (Google/Amazon) - Safe, Readable, Scalable Code.
import ast
import os
import re
import sys
import pytest
from fastapi.testclient import TestClient

if os.getcwd() not in sys.path:
    sys.path.insert(0, os.getcwd())


def _load_fastapi_app():
    """다양한 엔트리포인트(main.py, run.py, src/engine/main.py 등)에서 FastAPI app 인스턴스를 탐색."""
    for mod_name in ("main", "src.main", "src.engine.main", "run"):
        try:
            mod = __import__(mod_name, fromlist=["app"])
            if hasattr(mod, "app"):
                return mod.app
        except Exception:
            continue
    return None


@pytest.fixture
def client():
    """FastAPI 테스트 클라이언트 자동 바인딩 (main.py app 연동)."""
    app = _load_fastapi_app()
    if app is None:
        pytest.skip("FastAPI 메인 앱(main.py) 미도입 통과")
    return TestClient(app)


def _find_template_dirs() -> list[str]:
    """프로젝트 내 존재하는 모든 템플릿 디렉터리(전역 + 피처별 수직 슬라이스)를 누락 없이 합집합 탐색."""
    candidates = ["src/service/shell/templates", "src/templates", "templates"]
    found = [os.path.normpath(d) for d in candidates if os.path.exists(d)]
    if os.path.exists("src"):
        for root, dirs, _ in os.walk("src"):
            if "templates" in dirs:
                t_path = os.path.normpath(os.path.join(root, "templates"))
                if t_path not in found:
                    found.append(t_path)
    return found


def _find_base_html() -> str | None:
    """메인 레이아웃 base.html 경로 자동 탐색."""
    for t_dir in _find_template_dirs():
        candidate = os.path.join(t_dir, "base.html")
        if os.path.exists(candidate):
            return candidate
    if os.path.exists("src"):
        for root, _, files in os.walk("src"):
            if "base.html" in files:
                return os.path.join(root, "base.html")
    return None


def _find_shell_dirs() -> list[str]:
    """파이썬 백엔드 쉘 디렉터리 자동 탐색."""
    candidates = ["src/service/shell", "src/shell", "src/features", "src/engine"]
    found = [d for d in candidates if os.path.exists(d)]
    if not found and os.path.exists("src"):
        found = ["src"]
    return found


def _extract_all_route_paths(app) -> list[str]:
    """FastAPI 라우트 풀에서 _IncludedRouter 및 일반 Route를 전수 평탄화 추출."""
    paths: list[str] = []
    for r in getattr(app, "routes", []):
        p = getattr(r, "path", None)
        if p:
            paths.append(p)
        elif hasattr(r, "original_router"):
            for sub_r in getattr(r.original_router, "routes", []):
                sub_p = getattr(sub_r, "path", None)
                if sub_p:
                    paths.append(sub_p)
    return paths


# ==============================================================================
# 1. FastAPI 백엔드의 HTML 직접 조립(하드코딩) 침범 차단 가드
# ==============================================================================
def test_guard_fastapi_no_raw_html_hardcoding():
    """FastAPI 라우터/쉘 파이썬 파일 내부에서 HTML 태그 문자열 직접 조립 및 생 HTMLResponse 문자열 반환 금지."""
    shell_dirs = _find_shell_dirs()
    if not shell_dirs:
        pytest.skip("shell 디렉토리 미존재")

    raw_html_regex = re.compile(
        r"<(table|tr|td|th|div|span|form|p|ul|li|h[1-6]|button|input|section|article|nav|script)\b",
        re.IGNORECASE,
    )
    violations = []

    for s_dir in shell_dirs:
        for root, _, files in os.walk(s_dir):
            if "templates" in root:
                continue
            for file in files:
                if not file.endswith(".py"):
                    continue
                fpath = os.path.join(root, file)
                with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()

                match = raw_html_regex.search(content)
                if match:
                    violations.append(f"[{file}] 원시 태그({match.group(0)}) 하드코딩")

                try:
                    tree = ast.parse(content, filename=file)
                    for node in ast.walk(tree):
                        if (
                            isinstance(node, ast.Call)
                            and isinstance(node.func, ast.Name)
                            and node.func.id == "HTMLResponse"
                            and node.args
                            and isinstance(node.args[0], (ast.Constant, ast.JoinedStr))
                        ):
                            violations.append(
                                f"[{file}:{node.lineno}] HTMLResponse() 내부 문자열 직접 반환 금지"
                            )
                except SyntaxError:
                    continue

    assert not violations, (
        f"[1. FastAPI 영역침범 적발: {violations}]\n"
        f"AI 처방: 파이썬 코드 내 HTML 문자열 조립 금지 -> Jinja2 템플릿 파일로 분리 후 TemplateResponse로 렌더링하세요."
    )


# ==============================================================================
# 2. HTMX 요청 계약 가드 (HTML 조각 Fragment 반환 검증 - 정적 + 동적 이중 검증)
# ==============================================================================
def test_guard_htmx_returns_html_fragment(client: TestClient):
    """HTMX 헤더(HX-Request) 요청 및 조각 템플릿에서 전체 페이지(<!DOCTYPE/extends) 반환 차단."""
    # [정적 검증] components/ 또는 partials/ 하위 조각 템플릿에 <!DOCTYPE, <html, <body, {% extends 포함 차단
    template_dirs = _find_template_dirs()
    static_violations = []
    for t_dir in template_dirs:
        for root, _, files in os.walk(t_dir):
            rel_root = root.replace("\\", "/").lower()
            is_fragment_dir = any(k in rel_root for k in ("components", "partials", "fragments"))
            for file in files:
                if not file.endswith(".html"):
                    continue
                is_fragment_file = is_fragment_dir or file.startswith("_") or "fragment" in file.lower() or "partial" in file.lower()
                if not is_fragment_file:
                    continue
                fpath = os.path.join(root, file)
                with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                    text_lower = f.read().lower()
                if any(bad in text_lower for bad in ("<!doctype", "<html", "<body", "{% extends")):
                    static_violations.append(f"[{file}] 조각 템플릿 내 전체 페이지 태그/extends 포함")

    assert not static_violations, (
        f"[2. HTMX 조각 템플릿 규격 위반 적발: {static_violations}]\n"
        "AI 처방: 조각(components/partials) 템플릿에는 <!DOCTYPE/html/body/{% extends %}>를 넣지 말고 순수 HTML 조각만 작성하세요."
    )

    # [동적 검증] 등록된 라우트 중 파라미터 없는 /api/ 엔드포인트 런타임 응답 검사
    app = _load_fastapi_app()
    if app is None:
        return

    all_routes = _extract_all_route_paths(app)
    for path in all_routes:
        if path.startswith("/api/") and "static" not in path and "{" not in path:
            resp = client.get(path, headers={"HX-Request": "true"})
            if resp.status_code != 200:
                resp = client.post(path, headers={"HX-Request": "true"})
            if resp.status_code == 200 and "text/html" in resp.headers.get("content-type", ""):
                text = resp.text.strip().lower()
                assert "<!doctype html>" not in text and "<html" not in text and "<body" not in text, (
                    f"[2. HTMX 조각 규격 위반 적발: {path}]\n"
                    "AI 처방: HX-Request 요청에는 전체 페이지(<!DOCTYPE/html/body) 대신 교체할 순수 HTML 조각(Fragment)만 200 OK로 반환하세요."
                )


# ==============================================================================
# 3. 구식 폼 전송(MPA) 차단 및 HTMX 비동기 폼 강제 가드
# ==============================================================================
def test_guard_no_legacy_form_post_actions():
    """Jinja2 템플릿 내 전체 새로고침 구식 <form> 사용 차단 (HTMX hx-post/hx-get/hx-patch/hx-put/hx-delete 필수)."""
    template_dirs = _find_template_dirs()
    if not template_dirs:
        pytest.skip("템플릿 디렉토리 미존재")

    violations = []
    form_tag_regex = re.compile(r"<form\b[^>]*>", re.IGNORECASE)
    htmx_attrs = ("hx-post", "hx-get", "hx-put", "hx-patch", "hx-delete")

    for t_dir in template_dirs:
        for root, _, files in os.walk(t_dir):
            for file in files:
                if not file.endswith(".html"):
                    continue
                # 로그인 화면(/login)은 보안 쿠키 발급용 전통 폼 허용, 그 외 서비스 화면은 전원 HTMX 강제
                if file == "login.html":
                    continue

                fpath = os.path.join(root, file)
                with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()

                for match in form_tag_regex.finditer(content):
                    form_tag = match.group(0)
                    form_tag_lower = form_tag.lower()
                    if not any(attr in form_tag_lower for attr in htmx_attrs):
                        violations.append(f"[{file}] 구식 폼({form_tag[:50]}...)")

    assert not violations, (
        f"[3. HTMX 비동기 폼 누락 적발: {violations}]\n"
        f"AI 처방: 전체 새로고침 <form action=... method=POST> 금지 -> <form hx-post='/api/...' hx-target='#...' hx-swap='innerHTML'> 로 선언하고 백엔드에서 200 조각을 반환하세요."
    )


# ==============================================================================
# 4. HTMX 타겟 존재 유효성 검증 가드 (조각 분리 호환 + 타겟 오타 / 부재 차단)
# ==============================================================================
def _normalize_dynamic_id(raw_id: str) -> str:
    """Jinja2 동적 표현식(예: item-{{ item.id }})을 정규화하여 정적 접두사로 비교 가능하게 변환."""
    cleaned = re.sub(r"\{\{.*?\}\}", "*", raw_id)
    return cleaned.strip()


def test_guard_htmx_target_elements_exist():
    """모든 템플릿의 hx-target='#아이디'가 프로젝트 템플릿 풀(base + 페이지 + 조각) 내에 실제 존재하는지 검증."""
    template_dirs = _find_template_dirs()
    if not template_dirs:
        pytest.skip("템플릿 디렉토리 미존재")

    target_regex = re.compile(r'hx-target=[\"\']#([^\"\']+)[\"\']')
    id_regex = re.compile(r'\bid=[\"\']([^\"\']+)[\"\']')

    # 1단계: 프로젝트 내 모든 템플릿(base.html + 페이지 + components 조각)의 ID 풀(Pool) 수집
    global_id_pool: set[str] = set()
    html_files: list[tuple[str, str]] = []

    base_file = _find_base_html()
    if base_file and os.path.exists(base_file):
        with open(base_file, "r", encoding="utf-8", errors="ignore") as bf:
            for raw_id in id_regex.findall(bf.read()):
                global_id_pool.add(_normalize_dynamic_id(raw_id))

    for t_dir in template_dirs:
        for root, _, files in os.walk(t_dir):
            for file in files:
                if not file.endswith(".html"):
                    continue
                fpath = os.path.join(root, file)
                with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                html_files.append((file, content))
                for raw_id in id_regex.findall(content):
                    global_id_pool.add(_normalize_dynamic_id(raw_id))

    # 2단계: 각 템플릿의 hx-target='#...'가 전체 ID 풀에 존재하는지 대조
    missing_targets = []
    for file, content in html_files:
        for match in target_regex.finditer(content):
            raw_target = match.group(1).strip()
            # closest, find, next, this 등 셀렉터 수식어가 아닌 순수 #id 타겟만 검사
            if " " in raw_target:
                continue
            norm_target = _normalize_dynamic_id(raw_target)
            if norm_target not in global_id_pool:
                missing_targets.append(f"[{file}] #{raw_target}")

    assert not missing_targets, (
        f"\n[4. HTMX 타겟 미존재 적발: {missing_targets}]\n"
        f"AI 처방: hx-target에 지정된 ID 엘리먼트가 DOM에 없습니다. <div id='...'> 컨테이너를 생성하거나 올바른 id로 오타를 수정하세요."
    )
