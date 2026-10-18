# -*- coding: utf-8 -*-
# [파일명]: dashboard_core.py
# [목적]: 관제 대시보드 순수 비즈니스 연산 코어 (Pure Functional Core, 외부 I/O 0건)
from typing import Any, Final

# 비행 상태별 색상 및 애니메이션 디스패치 테이블 (T0 Table-Driven)
STATUS_STYLE_DISPATCH: Final[dict[str, dict[str, str]]] = {
    "IDLE": {
        "badge_class": "bg-slate-800 text-slate-300 border-slate-700",
        "color_class": "text-slate-400",
        "glow_class": "shadow-[0_0_10px_rgba(148,163,184,0.1)]",
        "pulse_class": "",
    },
    "ARMED": {
        "badge_class": "bg-amber-950 text-amber-300 border-amber-600",
        "color_class": "text-amber-400",
        "glow_class": "shadow-[0_0_12px_rgba(245,158,11,0.25)]",
        "pulse_class": "",
    },
    "TAKEOFF": {
        "badge_class": "bg-emerald-950 text-emerald-300 border-emerald-600",
        "color_class": "text-emerald-400",
        "glow_class": "shadow-[0_0_12px_rgba(16,185,129,0.25)]",
        "pulse_class": "animate-pulse",
    },
    "IN_FLIGHT": {
        "badge_class": "bg-cyan-950 text-cyan-300 border-cyan-500",
        "color_class": "text-cyan-400",
        "glow_class": "shadow-[0_0_15px_rgba(6,182,212,0.3)]",
        "pulse_class": "animate-pulse",
    },
    "LANDING": {
        "badge_class": "bg-blue-950 text-blue-300 border-blue-600",
        "color_class": "text-blue-400",
        "glow_class": "shadow-[0_0_12px_rgba(59,130,246,0.25)]",
        "pulse_class": "",
    },
    "EMERGENCY_RTH": {
        "badge_class": "bg-red-950 text-red-300 border-red-600",
        "color_class": "text-red-400",
        "glow_class": "shadow-[0_0_20px_rgba(239,68,68,0.5)]",
        "pulse_class": "animate-ping",
    },
    "LOST": {
        "badge_class": "bg-red-950 text-red-200 border-red-700",
        "color_class": "text-red-500",
        "glow_class": "shadow-[0_0_20px_rgba(239,68,68,0.6)]",
        "pulse_class": "animate-pulse",
    },
    "TERMINATED": {
        "badge_class": "bg-zinc-900 text-zinc-500 border-zinc-800",
        "color_class": "text-zinc-500",
        "glow_class": "",
        "pulse_class": "",
    },
}

DEFAULT_STYLE: Final[dict[str, str]] = {
    "badge_class": "bg-slate-800 text-slate-300 border-slate-700",
    "color_class": "text-slate-400",
    "glow_class": "",
    "pulse_class": "",
}


def _clamp(val: float, min_val: float, max_val: float) -> float:
    """수치를 min과 max 사이로 제한하는 순수 헬퍼."""
    return max(min_val, min(val, max_val))


def format_drone_card_data(raw: dict[str, Any]) -> dict[str, Any]:
    """단일 드론 텔레메트리 딕셔너리를 HUD 카드 렌더링 규격으로 살균 가공 (Pure Function)."""
    drone_id = str(raw.get("drone_id", "UNKNOWN")).strip()
    status = str(raw.get("status", "IDLE")).strip().upper()

    raw_battery = raw.get("battery", 0)
    try:
        battery_int = int(_clamp(float(raw_battery), 0.0, 100.0))
    except (ValueError, TypeError):
        battery_int = 0

    raw_alt = raw.get("altitude", 0.0)
    try:
        altitude_float = round(max(0.0, float(raw_alt)), 1)
    except (ValueError, TypeError):
        altitude_float = 0.0

    raw_speed = raw.get("speed", 0.0)
    try:
        speed_float = round(max(0.0, float(raw_speed)), 1)
    except (ValueError, TypeError):
        speed_float = 0.0

    is_emergency = status in ("EMERGENCY_RTH", "LOST")
    style_info = STATUS_STYLE_DISPATCH.get(status, DEFAULT_STYLE)

    # 배터리 잔량에 따른 원형 게이지 둘레 비율 (반지름 r=18, 둘레 C=2*pi*18 ~= 113.1)
    gauge_circumference = 113.1
    dash_offset = round(gauge_circumference * (1.0 - (battery_int / 100.0)), 1)

    # 배터리 위험도 색상
    if battery_int <= 15:
        battery_color_class = "text-red-400 stroke-red-500"
    elif battery_int <= 30:
        battery_color_class = "text-amber-400 stroke-amber-500"
    elif battery_int <= 70:
        battery_color_class = "text-cyan-400 stroke-cyan-500"
    else:
        battery_color_class = "text-emerald-400 stroke-emerald-500"

    return {
        "drone_id": drone_id,
        "status": status,
        "battery": battery_int,
        "altitude": altitude_float,
        "speed": speed_float,
        "latitude": round(float(raw.get("latitude", 0.0)), 6),
        "longitude": round(float(raw.get("longitude", 0.0)), 6),
        "timestamp": str(raw.get("timestamp", "-")),
        "is_emergency": is_emergency,
        "badge_class": style_info["badge_class"],
        "status_color_class": style_info["color_class"],
        "glow_class": style_info["glow_class"],
        "pulse_class": style_info["pulse_class"],
        "dash_offset": dash_offset,
        "battery_color_class": battery_color_class,
    }


def compute_dashboard_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    """다중 드론 텔레메트리 목록을 전술 요약 통계 및 HUD 카드로 집계 (Pure Function)."""
    if not records:
        return {
            "total_drones": 0,
            "active_in_flight": 0,
            "emergency_count": 0,
            "avg_battery": 0,
            "has_emergency": False,
            "drone_cards": [],
        }

    cards: list[dict[str, Any]] = [format_drone_card_data(r) for r in records]

    total_drones = len(cards)
    active_in_flight = sum(1 for c in cards if c["status"] == "IN_FLIGHT")
    emergency_count = sum(1 for c in cards if c["is_emergency"])
    total_battery = sum(c["battery"] for c in cards)
    avg_battery = int(total_battery / total_drones) if total_drones > 0 else 0

    return {
        "total_drones": total_drones,
        "active_in_flight": active_in_flight,
        "emergency_count": emergency_count,
        "avg_battery": avg_battery,
        "has_emergency": emergency_count > 0,
        "drone_cards": cards,
    }
