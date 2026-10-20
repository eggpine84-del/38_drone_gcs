# -*- coding: utf-8 -*-
# [파일명]: test_ui_markup_guard.py (대장 템플릿 - UI 템플릿 마크업 & 스타일 헌법 가드)
# [원칙] 1. 수동 JS 0줄(HTMX 전담) | 2. 인라인 픽셀 땜질 금지(Tailwind 전담) | 3. 300줄 이하 엄수
# [SYSTEM] Senior Staff Engineer (Google/Amazon) - Safe, Readable, Scalable Code.
import os
import re
import pytest

# 전역 모바일 프레임 등 정당한 고정 픽셀 화이트리스트
ALLOWED_ARBITRARY_PX = {"430px", "1px"}


def _find_template_dirs() -> list[str]:
    """프로젝트 내 존재하는 모든 템플릿 디렉터리(전역 + 피처별 수직 슬라이스)를 합집합으로 자동 탐색."""
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


def _strip_html_comments(html: str) -> str:
    """HTML 주석(<!-- ... -->)을 제거하여 주석 우회 및 주석 내 오탐을 방지합니다."""
    return re.sub(r"<!--.*?-->", "", html, flags=re.DOTALL)


# ==============================================================================
# 1. 자바스크립트 역할 침범 차단 가드 (JS Manual DOM/Fetch 금지)
# ==============================================================================
def test_guard_no_manual_js_dom_manipulation():
    """자바스크립트가 Jinja2/HTMX 역할을 침범하여 수동 fetch/innerHTML/XHR/onclick 조립하는 행위 원천 차단."""
    template_dirs = _find_template_dirs()
    if not template_dirs:
        pytest.skip("템플릿 디렉토리 미존재")

    banned_js_patterns = [
        (r"\bfetch\s*\(", "수동 fetch() 호출 금지 (HTMX hx-* 속성 사용 필수)"),
        (r"\.innerHTML\s*=", "자바스크립트 수동 innerHTML 조립 금지 (Jinja2 서버 렌더링 필수)"),
        (r"\.outerHTML\s*=", "자바스크립트 수동 outerHTML 조립 금지 (HTMX hx-swap 사용 필수)"),
        (r"\.insertAdjacentHTML\s*\(", "자바스크립트 수동 insertAdjacentHTML 금지 (HTMX hx-swap 사용 필수)"),
        (r"\baxios\.", "수동 axios 호출 금지 (HTMX 사용 필수)"),
        (r"\bnew\s+XMLHttpRequest\b", "수동 XMLHttpRequest 호출 금지 (HTMX 사용 필수)"),
        (r"\$\.(ajax|post|get)\s*\(", "수동 jQuery AJAX 호출 금지 (HTMX 사용 필수)"),
        (r"\bon(click|submit|change)\s*=", "구식 인라인 JS 이벤트(onclick/onsubmit 등) 금지 (HTMX hx-* 또는 Alpine @click 사용 필수)"),
    ]

    violations = []
    for t_dir in template_dirs:
        for root, _, files in os.walk(t_dir):
            for file in files:
                if not file.endswith(".html"):
                    continue
                fpath = os.path.join(root, file)
                with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                    content = _strip_html_comments(f.read())

                for pattern, reason in banned_js_patterns:
                    matches = re.finditer(pattern, content, flags=re.IGNORECASE)
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
    """메인 레이아웃(base.html)에 HTMX 및 Tailwind 공식 엔진 장착 필수 검증 (주석 우회 차단)."""
    base_path = _find_base_html()
    if not base_path:
        pytest.skip("base.html 미존재")

    with open(base_path, "r", encoding="utf-8", errors="ignore") as f:
        content = _strip_html_comments(f.read())

    has_htmx_script = bool(re.search(r"<script\b[^>]*src=[\"'][^\"']*htmx[^\"']*[\"']", content, re.IGNORECASE))
    assert has_htmx_script, (
        "[2. HTMX 엔진 누락 적발]\n"
        "AI 처방: base.html의 <head>에 <script src='https://unpkg.com/htmx.org@1.9.10'></script>를 반드시 배치하세요."
    )

    has_tailwind_tag = bool(
        re.search(r"<(script|link)\b[^>]*(src|href)=[\"'][^\"']*tailwind[^\"']*[\"']", content, re.IGNORECASE)
    )
    assert has_tailwind_tag, (
        "[2. Tailwind 엔진 누락 적발]\n"
        "AI 처방: base.html의 <head>에 <script src='https://cdn.tailwindcss.com'></script>를 반드시 배치하세요."
    )


# ==============================================================================
# 3. 인라인 픽셀 땜질(Pixel-Tug) 및 <style> 태그 남발 차단 가드
# ==============================================================================
def test_guard_no_excessive_inline_pixels():
    """템플릿 내 무분별한 인라인 style='...px', <style> 블록, Tailwind 임의 픽셀값(-[...px]) 도배 차단."""
    template_dirs = _find_template_dirs()
    if not template_dirs:
        pytest.skip("템플릿 디렉토리 미존재")

    violations = []
    arbitrary_px_regex = re.compile(r"-\[(\d+px)\]")

    for t_dir in template_dirs:
        for root, _, files in os.walk(t_dir):
            for file in files:
                if not file.endswith(".html"):
                    continue
                fpath = os.path.join(root, file)
                with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                    content = _strip_html_comments(f.read())

                # 1) 인라인 style="...px" 남발 검사
                pixel_matches = re.findall(r"style=[\"'][^\"']*\d+px[^\"']*[\"']", content, flags=re.IGNORECASE)
                if len(pixel_matches) > 3:
                    violations.append(f"[{file}] 인라인 style 픽셀 {len(pixel_matches)}건 남발")

                # 2) Tailwind 대괄호 임의 픽셀(예: w-[137px], mt-[23px]) 꼼수 남발 검사 (430px 등 규격 제외)
                arb_matches = [px for px in arbitrary_px_regex.findall(content) if px not in ALLOWED_ARBITRARY_PX]
                if len(arb_matches) > 3:
                    violations.append(f"[{file}] Tailwind 임의 픽셀값(-[...px]) {len(arb_matches)}건 남발: {arb_matches[:5]}")

                # 3) base.html 외 개별 조각/페이지 템플릿에 <style> 블록 직접 개설 차단
                if file != "base.html" and re.search(r"<style\b", content, flags=re.IGNORECASE):
                    violations.append(f"[{file}] 개별 템플릿 내 <style> 태그 직접 작성 금지 (Tailwind 유틸리티로 통일)")

    assert not violations, (
        f"[3. Tailwind 규격 위반 적발: {violations}]\n"
        f"AI 처방: style='...px' 인라인 땜질 금지 -> Tailwind 유틸리티 클래스(p-4, m-2, w-16, gap-3 등 8px 그리드)로 전면 교체하세요."
    )


# ==============================================================================
# 4. 서브탭 네비게이션 hx-boost 필수 가드 (탭 전환 깜빡임 차단 - 일반 border-b 오탐 제거)
# ==============================================================================
def test_guard_subtabs_use_hx_boost():
    """서브탭 네비게이션(?tab= 링크)이 hx-boost='true' 컨테이너 내부에 있거나 자체 hx-get/hx-boost를 갖는지 검증."""
    template_dirs = _find_template_dirs()
    if not template_dirs:
        pytest.skip("템플릿 디렉토리 미존재")

    violations = []
    # 1) 실제 ?tab= 쿼리를 가진 <a> 태그만 정밀 탐색 (일반 제목/구분선 border-b 오탐 원천 제거)
    tab_link_regex = re.compile(r"<a\b[^>]*href=[\"'][^\"']*\?tab=[^\"']*[\"'][^>]*>", re.IGNORECASE)
    # 2) 내부에 ?tab= 링크를 품고 있는 부모 컨테이너 블록 탐색
    tab_block_regex = re.compile(
        r"<(div|nav)\b([^>]*\bclass=[\"'][^\"']*border-b[^\"']*[\"'][^>]*)>((?:(?!</\1>).)*?\?tab=(?:(?!</\1>).)*?)</\1>",
        re.IGNORECASE | re.DOTALL,
    )

    for t_dir in template_dirs:
        for root, _, files in os.walk(t_dir):
            for file in files:
                if not file.endswith(".html"):
                    continue
                fpath = os.path.join(root, file)
                with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                    content = _strip_html_comments(f.read())

                if "?tab=" not in content:
                    continue

                # 파일 전체 또는 상위 레이아웃 차원에서 hx-boost="true"가 선언되어 있는지 확인
                file_has_hx_boost = bool(re.search(r"hx-boost=[\"']true[\"']", content, re.IGNORECASE))

                # A. ?tab= 링크를 실제로 감싸고 있는 border-b 탭 바 컨테이너 검사
                for match in tab_block_regex.finditer(content):
                    open_tag_attrs = match.group(2)
                    inner_html = match.group(3)
                    if "hx-boost" not in open_tag_attrs.lower() and "hx-get" not in inner_html.lower():
                        violations.append(f"[{file}] 서브탭 바(<{match.group(1)} {open_tag_attrs[:40].strip()}...>)")

                # B. border-b 컨테이너 밖에 단독으로 놓인 ?tab= 링크가 아무 HTMX 속성도 없는 경우 적발
                if not file_has_hx_boost:
                    for link_match in tab_link_regex.finditer(content):
                        a_tag = link_match.group(0).lower()
                        if not any(attr in a_tag for attr in ("hx-get", "hx-post", "hx-boost")):
                            violations.append(f"[{file}] 무속성 탭 링크({link_match.group(0)[:50]}...)")

    assert not violations, (
        f"\n[4. 서브탭 깜빡임(MPA) 적발: {violations}]\n"
        f"AI 처방: 서브탭 컨테이너 <div>에 hx-boost='true'를 추가하여 페이지 깜빡임 없이 즉각 전환되도록 하세요."
    )
