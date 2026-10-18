# -*- coding: utf-8 -*-
"""저장소 중립형 드론 텔레메트리 불변 원장 저장소 (Drone Ledger Repository).

CONSTITUTION.md 4대 공리 4항(원장 보존 및 다중 드론 격리) 및 3대 금기 3항(UPDATE/DELETE 전면 금지)을 준수.
인메모리(초고속 테스트) & SQLite(영구 보존) 듀얼 드라이버 지원.
"""
from abc import ABC, abstractmethod
import os
from typing import List, Optional

from src.engine.core.telemetry_record import TelemetryRecord
from src.engine.shell.db_adapter import execute_command, execute_query
from src.engine.shell.db_schema import init_db


class DroneLedgerRepository(ABC):
    """드론 원장 저장소 표준 추상 인터페이스 (Append-Only 불변 보존)."""

    @abstractmethod
    def append(self, record: TelemetryRecord) -> TelemetryRecord:
        """텔레메트리 레코드를 원장에 영구 추가합니다 (UPDATE/DELETE 영구 불가)."""
        pass

    @abstractmethod
    def get_latest(self, drone_id: str) -> Optional[TelemetryRecord]:
        """특정 드론의 가장 최신 텔레메트리 레코드를 조회합니다."""
        pass

    @abstractmethod
    def list_by_drone(self, drone_id: str, limit: int = 50) -> List[TelemetryRecord]:
        """특정 드론의 과거 비행 이력을 순차 조회합니다 (다중 드론 100% 격리)."""
        pass


class InMemoryDroneLedgerRepository(DroneLedgerRepository):
    """초고속 단위 테스트 및 인메모리 샌드박스용 원장 저장소."""

    def __init__(self) -> None:
        self._storage: List[TelemetryRecord] = []
        self._next_id: int = 1

    def append(self, record: TelemetryRecord) -> TelemetryRecord:
        assigned_id = self._next_id
        self._next_id += 1
        persisted = TelemetryRecord(
            id=assigned_id,
            drone_id=record.drone_id,
            latitude=record.latitude,
            longitude=record.longitude,
            altitude=record.altitude,
            speed=record.speed,
            battery=record.battery,
            status=record.status,
            timestamp=record.timestamp,
        )
        self._storage.append(persisted)
        return persisted

    def get_latest(self, drone_id: str) -> Optional[TelemetryRecord]:
        for rec in reversed(self._storage):
            if rec.drone_id == drone_id:
                return rec
        return None

    def list_by_drone(self, drone_id: str, limit: int = 50) -> List[TelemetryRecord]:
        matched = [r for r in self._storage if r.drone_id == drone_id]
        return matched[:limit]


class SqliteDroneLedgerRepository(DroneLedgerRepository):
    """SQLite 3대 헌법 기반 영구 원장 저장소 (100% 파라미터화 바인딩)."""

    def __init__(self, db_path: Optional[str] = None) -> None:
        self._db_path = db_path
        # 원장 테이블 자동 멱등 생성 보장
        init_db(self._db_path)

    def append(self, record: TelemetryRecord) -> TelemetryRecord:
        sql = (
            "INSERT INTO telemetry_logs "
            "(drone_id, latitude, longitude, altitude, speed, battery, status, timestamp) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?);"
        )
        params = (
            record.drone_id,
            record.latitude,
            record.longitude,
            record.altitude,
            record.speed,
            record.battery,
            record.status,
            record.timestamp,
        )
        row_id = execute_command(sql, params, db_path=self._db_path)
        return TelemetryRecord(
            id=row_id,
            drone_id=record.drone_id,
            latitude=record.latitude,
            longitude=record.longitude,
            altitude=record.altitude,
            speed=record.speed,
            battery=record.battery,
            status=record.status,
            timestamp=record.timestamp,
        )

    def get_latest(self, drone_id: str) -> Optional[TelemetryRecord]:
        sql = (
            "SELECT id, drone_id, latitude, longitude, altitude, speed, battery, status, timestamp "
            "FROM telemetry_logs WHERE drone_id = ? ORDER BY id DESC LIMIT 1;"
        )
        rows = execute_query(sql, (drone_id,), db_path=self._db_path)
        if not rows:
            return None
        r = rows[0]
        return TelemetryRecord(
            id=r["id"],
            drone_id=r["drone_id"],
            latitude=float(r["latitude"]),
            longitude=float(r["longitude"]),
            altitude=float(r["altitude"]),
            speed=float(r["speed"]),
            battery=int(r["battery"]),
            status=r["status"],
            timestamp=r["timestamp"],
        )

    def list_by_drone(self, drone_id: str, limit: int = 50) -> List[TelemetryRecord]:
        sql = (
            "SELECT id, drone_id, latitude, longitude, altitude, speed, battery, status, timestamp "
            "FROM telemetry_logs WHERE drone_id = ? ORDER BY id ASC LIMIT ?;"
        )
        rows = execute_query(sql, (drone_id, limit), db_path=self._db_path)
        return [
            TelemetryRecord(
                id=r["id"],
                drone_id=r["drone_id"],
                latitude=float(r["latitude"]),
                longitude=float(r["longitude"]),
                altitude=float(r["altitude"]),
                speed=float(r["speed"]),
                battery=int(r["battery"]),
                status=r["status"],
                timestamp=r["timestamp"],
            )
            for r in rows
        ]
