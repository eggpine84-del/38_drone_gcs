# -*- coding: utf-8 -*-
# [파일명]: mission_core.py
# [목적]: 비행 명령 유효성 검증 및 웨이포인트 진행률 순수 연산 코어 (외부 I/O 0건)
from dataclasses import dataclass
import math
from typing import Any, Final, Optional, Sequence


@dataclass(frozen=True)
class CommandResult:
    """비행 명령 판정 결과 불변 데이터 객체."""
    is_allowed: bool
    next_status: Optional[str]
    reason: str


@dataclass(frozen=True)
class ProgressResult:
    """웨이포인트 미션 진행률 결과 불변 데이터 객체."""
    current_index: int
    total_count: int
    progress_pct: int
    is_completed: bool


# 허용 명령 집합 (화이트리스트)
VALID_COMMANDS: Final[set[str]] = {"ARM", "TAKEOFF", "LAND", "RTH"}


def evaluate_command(
    current_status: str,
    command: str,
    battery: int
) -> CommandResult:
    """CONSTITUTION 5대 금기 1항(선행 상태 검증 없는 임의 비행 명령 차단) 순수 판정."""
    cmd = command.strip().upper()
    status = current_status.strip().upper()

    if cmd not in VALID_COMMANDS:
        return CommandResult(
            is_allowed=False,
            next_status=None,
            reason=f"정의되지 않은 비인가 명령입니다: '{command}'"
        )

    # 1. 시동 (ARM)
    if cmd == "ARM":
        if status != "IDLE":
            return CommandResult(
                is_allowed=False,
                next_status=None,
                reason=f"대기(IDLE) 상태에서만 시동(ARM)을 걸 수 있습니다. 현재 상태: {status}"
            )
        if battery <= 15:
            return CommandResult(
                is_allowed=False,
                next_status=None,
                reason=f"배터리 15% 이하({battery}%)에서는 안전을 위해 시동을 켤 수 없습니다."
            )
        return CommandResult(is_allowed=True, next_status="ARMED", reason="시동(ARMED) 승인 완료")

    # 2. 이륙 (TAKEOFF)
    if cmd == "TAKEOFF":
        if status != "ARMED":
            return CommandResult(
                is_allowed=False,
                next_status=None,
                reason=f"시동(ARMED) 상태에서만 이륙(TAKEOFF) 명령을 하달할 수 있습니다. 현재 상태: {status}"
            )
        if battery <= 15:
            return CommandResult(
                is_allowed=False,
                next_status=None,
                reason=f"배터리 15% 이하({battery}%)에서는 이륙 명령이 거부됩니다."
            )
        return CommandResult(is_allowed=True, next_status="TAKEOFF", reason="이륙(TAKEOFF) 승인 완료")

    # 3. 착륙 (LAND)
    if cmd == "LAND":
        if status not in ("IN_FLIGHT", "TAKEOFF"):
            return CommandResult(
                is_allowed=False,
                next_status=None,
                reason=f"비행(IN_FLIGHT/TAKEOFF) 상태에서만 착륙(LAND) 명령이 유효합니다. 현재 상태: {status}"
            )
        return CommandResult(is_allowed=True, next_status="LANDING", reason="착륙(LANDING) 절차 승인")

    # 4. 비상 귀환 (RTH)
    if cmd == "RTH":
        if status == "TERMINATED":
            return CommandResult(
                is_allowed=False,
                next_status=None,
                reason="이미 종료(TERMINATED)된 기체에는 귀환 명령을 하달할 수 없습니다."
            )
        return CommandResult(is_allowed=True, next_status="EMERGENCY_RTH", reason="비상 귀환(RTH) 발령")

    return CommandResult(is_allowed=False, next_status=None, reason="명령 처리 불가")


def validate_waypoints(waypoints: Sequence[dict[str, Any]]) -> bool:
    """웨이포인트 목록의 물리적 유효성 및 음수 고도(지하 충돌) 방어 (Pure Function)."""
    if not waypoints:
        return False

    for wp in waypoints:
        try:
            lat = float(wp.get("latitude", 0.0))
            lon = float(wp.get("longitude", 0.0))
            alt = float(wp.get("altitude", 0.0))

            if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
                return False
            # 지표면 이하(음수 고도) 충돌 방어
            if alt < 0.0 or alt > 500.0:
                return False
        except (ValueError, TypeError):
            return False

    return True


def _haversine_distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """두 좌표 간의 구면 대원 거리(미터) 계산 순수 헬퍼."""
    r = 6371000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2.0) ** 2
    a = min(1.0, max(0.0, a))
    return r * 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))


def calculate_waypoint_progress(
    current_lat: float,
    current_lon: float,
    current_alt: float,
    waypoints: Sequence[dict[str, Any]],
    current_index: int,
    arrival_threshold_m: float = 5.0,
) -> ProgressResult:
    """현재 드론 좌표 기반 3차원 도달 판정 및 미션 진행률(0~100%) 계산 (Pure Function)."""
    total = len(waypoints)
    if total == 0:
        return ProgressResult(current_index=0, total_count=0, progress_pct=0, is_completed=True)

    idx = max(0, min(current_index, total))
    if idx >= total:
        return ProgressResult(current_index=total, total_count=total, progress_pct=100, is_completed=True)

    target_wp = waypoints[idx]
    t_lat = float(target_wp.get("latitude", 0.0))
    t_lon = float(target_wp.get("longitude", 0.0))
    t_alt = float(target_wp.get("altitude", 0.0))

    # 3차원 거리 계산 (수평 거리 + 고도 차이)
    h_dist = _haversine_distance_m(current_lat, current_lon, t_lat, t_lon)
    v_dist = abs(current_alt - t_alt)
    total_dist = math.sqrt(h_dist ** 2 + v_dist ** 2)

    # 목표 지점 도달 시 다음 인덱스로 전진
    if total_dist <= arrival_threshold_m:
        idx += 1

    is_completed = (idx >= total)
    progress_pct = int((idx / total) * 100) if total > 0 else 0

    return ProgressResult(
        current_index=idx,
        total_count=total,
        progress_pct=progress_pct,
        is_completed=is_completed,
    )
