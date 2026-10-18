# -*- coding: utf-8 -*-
# [파일명]: dashboard_routes.py
# [목적]: 관제 대시보드 웹 화면 및 HTMX 실시간 조각 라우터
import os
from typing import Any
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from src.features.dashboard.core.dashboard_core import compute_dashboard_summary
from src.features.dashboard.shell.dashboard_repository import get_all_active_drones_latest

router = APIRouter(tags=["Dashboard"])

# 템플릿 검색 경로 (피처 전용 템플릿 + 공통 베이스 템플릿)
_template_dirs = [
    os.path.join("src", "features", "dashboard", "shell", "templates"),
    os.path.join("src", "templates"),
]
templates = Jinja2Templates(directory=_template_dirs)


@router.get("/", response_class=HTMLResponse)
def get_dashboard_page(request: Request) -> Any:
    """메인 전술 관제탑 전체 페이지 렌더링 (GET /)."""
    records = get_all_active_drones_latest()
    summary = compute_dashboard_summary(records)
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={"summary": summary},
    )


@router.get("/api/features/dashboard/stream", response_class=HTMLResponse)
def get_dashboard_stream(request: Request) -> Any:
    """HTMX 실시간 폴링용 순수 HTML 조각(Fragment) 렌더링."""
    records = get_all_active_drones_latest()
    summary = compute_dashboard_summary(records)
    return templates.TemplateResponse(
        request=request,
        name="drone_card_fragment.html",
        context={"summary": summary},
    )
