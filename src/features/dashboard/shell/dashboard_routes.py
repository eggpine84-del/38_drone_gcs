# -*- coding: utf-8 -*-
# [파일명]: dashboard_routes.py
# [목적]: 관제 대시보드 웹 화면 및 HTMX 실시간 조각 라우터
import os
from typing import Any
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from src.engine.core.mavlink_parser_core import resolve_active_drone_id
from src.features.dashboard.core.dashboard_core import compute_dashboard_summary
from src.features.dashboard.shell.dashboard_repository import get_all_active_drones_latest
from src.features.dashboard.shell.command_dto import DroneCommandIn
from src.features.dashboard.shell.flight_command_service import get_flight_command_service

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
    available_ids = [r["drone_id"] for r in records if "drone_id" in r]
    default_id = (os.environ.get("DEFAULT_DRONE_ID") or "DRONE-01").strip() or "DRONE-01"

    requested_id = request.query_params.get("drone_id", "").strip()
    if requested_id and (requested_id in available_ids or requested_id == default_id):
        active_drone_id = requested_id
    else:
        active_drone_id = resolve_active_drone_id(available_ids, default_fallback=default_id)

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "summary": summary,
            "active_drone_id": active_drone_id,
            "available_drones": available_ids if available_ids else [active_drone_id],
        },
    )


@router.get("/api/features/dashboard/stream", response_class=HTMLResponse)
def get_dashboard_stream(request: Request) -> Any:
    """HTMX 실시간 폴링용 순수 HTML 조각(Fragment) 렌더링."""
    records = get_all_active_drones_latest()
    summary = compute_dashboard_summary(records)
    available_ids = [r["drone_id"] for r in records if "drone_id" in r]
    default_id = (os.environ.get("DEFAULT_DRONE_ID") or "DRONE-01").strip() or "DRONE-01"

    requested_id = request.query_params.get("drone_id", "").strip()
    if requested_id and (requested_id in available_ids or requested_id == default_id):
        active_drone_id = requested_id
    else:
        active_drone_id = resolve_active_drone_id(available_ids, default_fallback=default_id)

    return templates.TemplateResponse(
        request=request,
        name="drone_card_fragment.html",
        context={
            "summary": summary,
            "active_drone_id": active_drone_id,
            "available_drones": available_ids if available_ids else [active_drone_id],
        },
    )


@router.post("/api/features/dashboard/command")
async def send_flight_command(request: Request) -> Any:
    """비행 제어 명령 송출 엔드포인트 (HTMX 및 B1 단일 봉투 공용)."""
    content_type = request.headers.get("content-type", "")
    try:
        if "application/json" in content_type:
            body = await request.json()
        else:
            form = await request.form()
            body = dict(form)
            for p in ("param1", "param2", "param3", "param4"):
                if p in body:
                    try:
                        body[p] = float(body[p])
                    except (ValueError, TypeError):
                        body[p] = 0.0

        cmd = DroneCommandIn(**body)
    except Exception as exc:
        if request.headers.get("HX-Request"):
            return templates.TemplateResponse(
                request=request,
                name="command_feedback.html",
                context={"success": False, "error_message": str(exc)},
                status_code=400,
            )
        return JSONResponse(
            status_code=400,
            content={"success": False, "data": None, "error": {"code": "VAL_ERR", "message": str(exc)}},
        )

    service = get_flight_command_service()
    result = service.dispatch_command(cmd)

    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(
            request=request,
            name="command_feedback.html",
            context={"success": True, "command": cmd.command},
            status_code=200,
        )

    return JSONResponse(
        status_code=200,
        content={"success": True, "data": result, "error": None},
    )
