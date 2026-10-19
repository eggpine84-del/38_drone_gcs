# -*- coding: utf-8 -*-
"""전술 서랍 상단 탑-다운(Top-down) 반응형 패널 및 순수 CSS Peer 개폐 핀-테스트.

FCIS 및 Pin-Test First 원칙:
1. details 태그 부재 검증 (헤더 밀림/덜컹거림 CLS 원천 차단).
2. peer 체크박스(input#tactical-drawer-toggle) 및 토글 라벨 바인딩 검증.
3. 상단 탑-다운 드롭다운 패널(hidden peer-checked:block) 검증.
4. 배경 흐림 차단: 전체화면 백드롭(fixed inset-0 backdrop-blur) 부재 검증 (관제탑 선명도 100% 유지).
5. 서랍 내부 닫기 트리거(label for="tactical-drawer-toggle") 검증.
"""
import os
import re
import pytest


@pytest.fixture
def dashboard_html() -> str:
    """dashboard.html 원본 템플릿 파일 로드."""
    tmpl_path = os.path.join(
        "src", "features", "dashboard", "shell", "templates", "dashboard.html"
    )
    with open(tmpl_path, "r", encoding="utf-8") as f:
        return f.read()


def test_pin_tactical_drawer_markup(dashboard_html: str):
    """전술 서랍의 상단 탑-다운 패널 및 배경 비흐림(무백드롭) 마크업 규격 검증."""
    # 1. 헤더 밀림을 유발하던 레거시 details 태그 전면 제거 검증
    assert "<details" not in dashboard_html, "헤더를 밀어내던 레거시 <details> 태그가 존재합니다."

    # 2. 피어 체크박스 토글 존재 검증
    assert 'id="tactical-drawer-toggle"' in dashboard_html, "id='tactical-drawer-toggle' 체크박스가 필요합니다."
    assert 'type="checkbox"' in dashboard_html, "type='checkbox' 토글이 필요합니다."
    assert 'peer hidden' in dashboard_html, "peer hidden 클래스가 필요합니다."

    # 3. 상단 헤더의 열기 라벨 버튼 검증
    assert 'for="tactical-drawer-toggle"' in dashboard_html, "for='tactical-drawer-toggle' 라벨이 필요합니다."
    assert 'drawer-toggle-btn' in dashboard_html, "drawer-toggle-btn 클래스가 필요합니다."

    # 4. 배경 화면 흐림(블러/어두운 백드롭) 차단 검증 (관제탑 선명도 100% 유지)
    assert 'backdrop-blur-sm z-40' not in dashboard_html, "관제탑 화면을 흐리게 가리는 전체화면 백드롭은 없어야 합니다."

    # 5. 상단에서 아래로 내려오는 탑-다운 서랍 패널 검증
    assert 'tactical-drawer-panel' in dashboard_html, "tactical-drawer-panel 클래스가 필요합니다."
    assert 'hidden' in dashboard_html and 'peer-checked:block' in dashboard_html, "순수 CSS 탑-다운 토글(hidden peer-checked:block)이 필요합니다."

    # 6. 서랍 내부 닫기 라벨 버튼 검증
    close_pattern = r'label[^>]*for="tactical-drawer-toggle"[\s\S]*?닫기[\s\S]*?</label>'
    assert re.search(close_pattern, dashboard_html), "서랍 내부에 for='tactical-drawer-toggle' 닫기 라벨 버튼이 필요합니다."

