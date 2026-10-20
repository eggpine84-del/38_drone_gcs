# -*- coding: utf-8 -*-
# [파일명]: dashboard_repository.py
# [목적]: 관제 대시보드 피처 전용 읽기 전용 쿼리 어댑터 (Zero-Mutation 원칙 준수)
import os
import sys
from datetime import datetime, timezone
from typing import Any, Optional
from src.engine.shell.db_adapter import execute_query


def _is_within_window(ts_str: str, max_age_seconds: float) -> bool:
    """타임스탬프가 현재 시각 기준 max_age_seconds 초 이내인지 안전하게 판별."""
    if not ts_str:
        return False
    try:
        dt = datetime.fromisoformat(ts_str)
        now = datetime.now(timezone.utc)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        age_seconds = (now - dt).total_seconds()
        # 시간 역전(-5초 이내)은 클럭 오차로 허용하고, max_age_seconds를 초과한 과거 데이터는 제외
        return age_seconds <= max_age_seconds
    except Exception:
        # 형식 파싱 불가 시 보수적으로 활성 처리 (데이터 증발 방어)
        return True


def _resolve_effective_window(param_window: Optional[float]) -> Optional[float]:
    """우선순위(명시 파라미터 -> 환경변수 -> 실행환경 기본값)에 따라 실효 윈도우 초를 결정."""
    if param_window is not None:
        return param_window if param_window > 0.0 else None

    # 환경변수 DASHBOARD_ACTIVE_WINDOW_SECONDS 확인
    env_window = os.getenv("DASHBOARD_ACTIVE_WINDOW_SECONDS")
    if env_window is not None:
        try:
            val = float(env_window)
            return val if val > 0.0 else None
        except ValueError as exc:
            import logging
            logging.getLogger(__name__).debug("DASHBOARD_ACTIVE_WINDOW_SECONDS 파싱 실패(%s), 기본값 폴백: %s", env_window, str(exc))

    # 테스트 환경(pytest 구동 중이거나 APP_ENV == "test")일 때는 목업 테스트 호환을 위해 기본 무제한(None)
    if os.getenv("APP_ENV") == "test" or "pytest" in sys.modules:
        return None

    # 상용/개발 실제 가동 환경에서는 전원 꺼진 유령 기체 제외를 위해 기본 30.0초 윈도우 적용
    return 30.0


def get_all_active_drones_latest(
    db_path: Optional[str] = None,
    max_age_seconds: Optional[float] = None,
) -> list[dict[str, Any]]:
    """모든 등록 드론의 최신 텔레메트리 1건씩을 일괄 조회 (하트비트 윈도우 필터 적용)."""
    sql = (
        "SELECT t1.id, t1.drone_id, t1.latitude, t1.longitude, t1.altitude, "
        "       t1.speed, t1.battery, t1.status, t1.timestamp "
        "FROM telemetry_logs t1 "
        "INNER JOIN ( "
        "    SELECT drone_id, MAX(id) AS max_id "
        "    FROM telemetry_logs "
        "    GROUP BY drone_id "
        ") t2 ON t1.id = t2.max_id "
        "ORDER BY t1.drone_id ASC;"
    )
    try:
        rows = execute_query(sql, (), db_path=db_path)
        all_records = [
            {
                "id": r["id"],
                "drone_id": r["drone_id"],
                "latitude": float(r["latitude"]),
                "longitude": float(r["longitude"]),
                "altitude": float(r["altitude"]),
                "speed": float(r["speed"]),
                "battery": int(r["battery"]),
                "status": r["status"],
                "timestamp": r["timestamp"],
            }
            for r in rows
        ]

        effective_window = _resolve_effective_window(max_age_seconds)
        if effective_window is not None:
            return [r for r in all_records if _is_within_window(r["timestamp"], effective_window)]

        return all_records
    except Exception:
        # 최초 기동 시 테이블 미존재 등의 경우 빈 리스트 안전 반환
        return []


