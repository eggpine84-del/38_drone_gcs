# -*- coding: utf-8 -*-
# [파일명]: test_ui_markup_guard.py (대장 템플릿 - UI 템플릿 마크업 & 스타일 헌법 가드)
# [원칙] 1. 수동 JS 0줄(HTMX 전담) | 2. 인라인 픽셀 땜질 금지(Tailwind 전담) | 3. 300줄 이하 엄수
# [SYSTEM] Senior Staff Engineer (Google/Amazon) - Safe, Readable, Scalable Code.
import os
import re
import pytest


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


# ==============================================================================
# 1. 자바스크립트 역할 침범 차단 가드 (JS Manual DOM/Fetch 금지)
# ==============================================================================
def test_guard_no_manual_js_dom_manipulation():
    """자바스크립트가 Jinja2/HTMX 역할을 침범하여 수동 fetch/innerHTML 조립하는 행위 원천 차단."""
    template_dirs = _find_template_dirs()
    if not template_dirs:
        pytest.skip("템플릿 디렉토리 미존재")

    banned_js_patterns = [
        (r"fetch\s*\(", "수동 fetch() 호출 금지 (HTMX hx-* 속성 사용 필수)"),
        (r"\.innerHTML\s*=", "자바스크립트 수동 innerHTML 조립 금지 (Jinja2 서버 렌더링 필수)"),
        (r"\.insertAdjacentHTML\s*\(", "자바스크립트 수동 insertAdjacentHTML 금지 (HTMX hx-swap 사용 필수)"),
        (r"axios\.", "수동 axios 호출 금지 (HTMX 사용 필수)")
    ]

    violations = []
    for t_dir in template_dirs:
        for root, _, files in os.walk(t_dir):
            for file in files:
                if not file.endswith(".html"):
                    continue
                fpath = os.path.join(root, file)
                with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()

                for pattern, reason in banned_js_patterns:
                    matches = re.finditer(pattern, content)
                    for m in matches:
                        violations.append(f"[{file}] {reason} (위치: {m.start()})")

    remediation_guide = (
        "\n[UI 방탄 가드: JS 작성 즉각 차단]\n"
        "[절대금지]: Vercel 서버리스 크롤링 우회 금지 | 인메모리 큐 폴링 금지\n"
        "[정석공식]: 자바스크립트 0줄 구현 필수\n"
        " 1. 프론트: <button hx-post=\"/api/...\" hx-target=\"#결과영역\" hx-swap=\"innerHTML\">\n"
        " 2. 백엔드: 완성된 HTML 테이블 조각(Fragment) 200 OK 반환 (HTMX 자동 꽂기)\n"
    )
    assert not violations, f"{remediation_guide}\n자바스크립트 역할 침범 적발: {violations}"


# ==============================================================================
# 2. 필수 엔진(HTMX / Tailwind) 공식 탑재 가드
# ==============================================================================
def test_guard_base_template_engines_loaded():
    """메인 레이아웃(base.html)에 HTMX 및 Tailwind 공식 엔진 장착 필수 검증."""
    base_path = _find_base_html()
    if not base_path:
        pytest.skip("base.html 미존재")

    with open(base_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    assert "htmx.org" in content, (
        "[2. HTMX 엔진 누락 적발]\n"
        "AI 처방: base.html의 <head>에 <script src='https://unpkg.com/htmx.org@1.9.10'></script>를 반드시 배치하세요."
    )
    assert "tailwindcss.com" in content or "tailwind" in content.lower(), (
        "[2. Tailwind 엔진 누락 적발]\n"
        "AI 처방: base.html의 <head>에 <script src='https://cdn.tailwindcss.com'></script>를 반드시 배치하세요."
    )


# ==============================================================================
# 3. 인라인 픽셀 땜질(Pixel-Tug) 차단 가드
# ==============================================================================
def test_guard_no_excessive_inline_pixels():
    """템플릿 내 무분별한 인라인 style=\"px\" 조작 차단 (Tailwind 유틸리티 클래스 사용 강제)."""
    template_dirs = _find_template_dirs()
    if not template_dirs:
        pytest.skip("템플릿 디렉토리 미존재")

    violations = []
    for t_dir in template_dirs:
        for root, _, files in os.walk(t_dir):
            for file in files:
                if not file.endswith(".html"):
                    continue
                fpath = os.path.join(root, file)
                with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()

                pixel_matches = re.findall(r"style=[\"'][^\"']*\d+px[^\"']*[\"']", content)
                if len(pixel_matches) > 3:
                    violations.append(f"[{file}] 인라인 픽셀 {len(pixel_matches)}건 남발")

    assert not violations, (
        f"[3. Tailwind 규격 위반 적발: {violations}]\n"
        f"AI 처방: style='...px' 인라인 땜질 금지 -> Tailwind 유틸리티 클래스(p-4, m-2, w-16, gap-3 등 8px 그리드)로 전면 교체하세요."
    )


# ==============================================================================
# 4. 서브탭 네비게이션 hx-boost 필수 가드 (탭 전환 깜빡임 차단)
# ==============================================================================
def test_guard_subtabs_use_hx_boost():
    """서브탭 네비게이션(?tab= 링크 컨테이너)에 hx-boost='true' 탑재 필수 검증."""
    template_dirs = _find_template_dirs()
    if not template_dirs:
        pytest.skip("템플릿 디렉토리 미존재")

    violations = []
    tab_container_regex = re.compile(r'<div\s+([^>]*\bclass=[\"\'][^\"\']*border-b[^\"\']*[\"\'][^>]*)>', re.IGNORECASE)

    for t_dir in template_dirs:
        for root, _, files in os.walk(t_dir):
            for file in files:
                if not file.endswith(".html"):
                    continue
                fpath = os.path.join(root, file)
                with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()

                if "?tab=" not in content:
                    continue

                for match in tab_container_regex.finditer(content):
                    container_tag = match.group(0)
                    if "hx-boost" not in container_tag:
                        violations.append(f"[{file}] 서브탭 바({container_tag[:50]}...)")

    assert not violations, (
        f"\n[4. 서브탭 깜빡임(MPA) 적발: {violations}]\n"
        f"AI 처방: 서브탭 컨테이너 <div>에 hx-boost='true'를 추가하여 페이지 깜빡임 없이 즉각 전환되도록 하세요."
    )
