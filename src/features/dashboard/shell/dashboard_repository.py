# -*- coding: utf-8 -*-
# [파일명]: dashboard_repository.py
# [목적]: 관제 대시보드 피처 전용 읽기 전용 쿼리 어댑터 (Zero-Mutation 원칙 준수)
from typing import Any, Optional
from src.engine.shell.db_adapter import execute_query


def get_all_active_drones_latest(db_path: Optional[str] = None) -> list[dict[str, Any]]:
    """모든 등록 드론의 최신 텔레메트리 1건씩을 일괄 조회 (읽기 전용 그룹화 쿼리)."""
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
        return [
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
    except Exception:
        # 최초 기동 시 테이블 미존재 등의 경우 빈 리스트 안전 반환
        return []
