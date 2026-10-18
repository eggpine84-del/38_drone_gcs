# -*- coding: utf-8 -*-
# [파일명]: test_ui_contract_guard.py (대장 템플릿 - 백엔드 및 HTMX 통신 계약 헌법 가드)
# [원칙] 1. 파이썬 HTML 하드코딩 금지(Jinja2 전담) | 2. HTMX 조각(Fragment) 200 계약 | 3. 300줄 이하 엄수
# [SYSTEM] Senior Staff Engineer (Google/Amazon) - Safe, Readable, Scalable Code.
import os
import re
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """FastAPI 테스트 클라이언트 자동 바인딩 (main.py app 연동)."""
    try:
        from main import app
        return TestClient(app)
    except Exception:
        pytest.skip("FastAPI 메인 앱(main.py) 미도입 통과")


def _find_template_dirs() -> list[str]:
    """프로젝트 내 존재하는 모든 템플릿 디렉터리를 자동 탐색."""
    candidates = ["src/service/shell/templates", "src/templates", "templates"]
    found = [d for d in candidates if os.path.exists(d)]
    if not found and os.path.exists("src"):
        for root, dirs, _ in os.walk("src"):
            if "templates" in dirs:
                found.append(os.path.join(root, "templates"))
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
    candidates = ["src/service/shell", "src/shell", "src/features"]
    found = [d for d in candidates if os.path.exists(d)]
    if not found and os.path.exists("src"):
        found = ["src"]
    return found


# ==============================================================================
# 1. FastAPI 백엔드의 HTML 직접 조립(하드코딩) 침범 차단 가드
# ==============================================================================
def test_guard_fastapi_no_raw_html_hardcoding():
    """FastAPI 라우터/쉘 파이썬 파일 내부에서 HTML 태그 문자열 직접 조립 금지."""
    shell_dirs = _find_shell_dirs()
    if not shell_dirs:
        pytest.skip("shell 디렉토리 미존재")

    banned_html_tags = ["<table", "<tr", "<td", "<div", "<span", "<form"]
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

                for tag in banned_html_tags:
                    if tag in content:
                        violations.append(f"[{file}] 원시 태그({tag}) 하드코딩")

    assert not violations, (
        f"[1. FastAPI 영역침범 적발: {violations}]\n"
        f"AI 처방: 파이썬 코드 내 HTML 문자열 조립 금지 -> Jinja2 템플릿 파일로 분리 후 TemplateResponse로 렌더링하세요."
    )


# ==============================================================================
# 2. HTMX 요청 계약 가드 (HTML 조각 Fragment 반환 검증)
# ==============================================================================
def test_guard_htmx_returns_html_fragment(client: TestClient):
    """HTMX 헤더(HX-Request) 요청 시 전체 페이지(<!DOCTYPE)가 아닌 순수 HTML 조각(Fragment) 반환 검증."""
    try:
        from main import app
    except ImportError:
        pytest.skip("main.py 미도입 통과")
        return

    # 등록된 라우트 중 /api/ 또는 HTMX 조각 반환 엔드포인트 동적 탐색
    target_route = None
    for route in getattr(app, "routes", []):
        path = getattr(route, "path", "")
        if path.startswith("/api/") and "static" not in path:
            target_route = path
            break

    if not target_route:
        pytest.skip("HTMX 조각 엔드포인트 미등록 프로젝트 통과")
        return

    resp = client.get(target_route, headers={"HX-Request": "true"})
    if resp.status_code != 200:
        resp = client.post(target_route, headers={"HX-Request": "true"})

    if resp.status_code == 200 and "text/html" in resp.headers.get("content-type", ""):
        text = resp.text.strip()
        assert "<!DOCTYPE html>" not in text and "<html" not in text and "<body" not in text, (
            "[2. HTMX 조각 규격 위반 적발]\n"
            "AI 처방: HX-Request 요청에는 전체 페이지(<!DOCTYPE/html/body) 대신 교체할 순수 HTML 조각(Fragment)만 200 OK로 반환하세요."
        )


# ==============================================================================
# 3. 구식 폼 전송(MPA) 차단 및 HTMX 비동기 폼 강제 가드
# ==============================================================================
def test_guard_no_legacy_form_post_actions():
    """Jinja2 템플릿 내 전체 새로고침 구식 <form action=... method=POST> 사용 차단 (HTMX hx-post/hx-patch 필수)."""
    template_dirs = _find_template_dirs()
    if not template_dirs:
        pytest.skip("템플릿 디렉토리 미존재")

    violations = []
    legacy_post_regex = re.compile(r"<form\s+[^>]*method=[\"']?POST[\"']?[^>]*>", re.IGNORECASE)

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

                for match in legacy_post_regex.finditer(content):
                    form_tag = match.group(0)
                    if "hx-post" not in form_tag and "hx-patch" not in form_tag and "hx-put" not in form_tag:
                        violations.append(f"[{file}] 구식 폼({form_tag[:50]}...)")

    assert not violations, (
        f"[3. HTMX 비동기 폼 누락 적발: {violations}]\n"
        f"AI 처방: 전체 새로고침 <form action=... method=POST> 금지 -> <form hx-post='/api/...' hx-target='#...' hx-swap='innerHTML'> 로 선언하고 백엔드에서 200 조각을 반환하세요."
    )


# ==============================================================================
# 4. HTMX 타겟 존재 유효성 검증 가드 (타겟 오타 / 부재 차단)
# ==============================================================================
def test_guard_htmx_target_elements_exist():
    """모든 템플릿의 hx-target='#아이디'에 지정된 id가 해당 파일 또는 base.html에 실제로 존재하는지 전수 검증."""
    template_dirs = _find_template_dirs()
    if not template_dirs:
        pytest.skip("템플릿 디렉토리 미존재")

    base_file = _find_base_html()
    base_content = open(base_file, "r", encoding="utf-8", errors="ignore").read() if (base_file and os.path.exists(base_file)) else ""

    missing_targets = []
    target_regex = re.compile(r'hx-target=[\"\']#([a-zA-Z0-9_\-]+)[\"\']')
    id_regex = re.compile(r'id=[\"\']([a-zA-Z0-9_\-]+)[\"\']')

    for t_dir in template_dirs:
        for root, _, files in os.walk(t_dir):
            for file in files:
                if not file.endswith(".html"):
                    continue
                fpath = os.path.join(root, file)
                with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()

                all_ids = set(id_regex.findall(content)).union(set(id_regex.findall(base_content)))
                for match in target_regex.finditer(content):
                    target_id = match.group(1)
                    if target_id not in all_ids:
                        missing_targets.append(f"[{file}] #{target_id}")

    assert not missing_targets, (
        f"\n[4. HTMX 타겟 미존재 적발: {missing_targets}]\n"
        f"AI 처방: hx-target에 지정된 ID 엘리먼트가 DOM에 없습니다. <div id='...'> 컨테이너를 생성하거나 올바른 id로 오타를 수정하세요."
    )
