# -*- coding: utf-8 -*-
# [파일명]: test_pin_drone_repository.py (저장소 중립형 불변 원장 저장소 선행 핀-테스트)
# [원칙] 1. 인메모리 & SQLite 듀얼 드라이버 1:1 대칭 검증 | 2. drone_id별 완전 격리 | 3. UPDATE/DELETE 부재(Append-Only)
import pytest
from src.engine.core.telemetry_record import TelemetryRecord
from src.engine.shell.drone_repository import (
    InMemoryDroneLedgerRepository,
    SqliteDroneLedgerRepository,
)


@pytest.fixture(params=["in_memory", "sqlite"])
def repo(request, tmp_path):
    """인메모리와 SQLite 듀얼 드라이버를 동일 테스트 케이스로 100% 대칭 검증."""
    if request.param == "in_memory":
        return InMemoryDroneLedgerRepository()
    db_file = str(tmp_path / "test_ledger.db")
    return SqliteDroneLedgerRepository(db_path=db_file)


def test_pin_append_and_get_latest(repo):
    """기본 적재 및 최신 텔레메트리 조회 검증 (Full-Assertion)."""
    rec1 = TelemetryRecord(
        drone_id="DRONE-01",
        latitude=37.5665,
        longitude=126.9780,
        altitude=50.0,
        speed=12.5,
        battery=85,
        status="IN_FLIGHT",
        timestamp="2026-10-18T14:00:00Z",
    )
    rec2 = TelemetryRecord(
        drone_id="DRONE-01",
        latitude=37.5670,
        longitude=126.9785,
        altitude=55.0,
        speed=13.0,
        battery=84,
        status="IN_FLIGHT",
        timestamp="2026-10-18T14:00:01Z",
    )

    saved1 = repo.append(rec1)
    saved2 = repo.append(rec2)

    assert saved1.id is not None
    assert saved2.id is not None

    latest = repo.get_latest("DRONE-01")
    assert latest is not None
    assert latest.drone_id == "DRONE-01"
    assert latest.latitude == 37.5670
    assert latest.battery == 84
    assert latest.timestamp == "2026-10-18T14:00:01Z"


def test_pin_multi_drone_isolation(repo):
    """공리 4(다중 드론 격리): A 드론 데이터 조회 시 B 드론 데이터 절대 불포함 (Full-Assertion)."""
    rec_a = TelemetryRecord(
        drone_id="DRONE-A",
        latitude=37.1111,
        longitude=126.1111,
        altitude=30.0,
        speed=10.0,
        battery=90,
        status="ARMED",
        timestamp="2026-10-18T14:00:00Z",
    )
    rec_b = TelemetryRecord(
        drone_id="DRONE-B",
        latitude=38.2222,
        longitude=127.2222,
        altitude=40.0,
        speed=15.0,
        battery=70,
        status="IN_FLIGHT",
        timestamp="2026-10-18T14:00:00Z",
    )

    repo.append(rec_a)
    repo.append(rec_b)

    logs_a = repo.list_by_drone("DRONE-A")
    logs_b = repo.list_by_drone("DRONE-B")

    assert len(logs_a) == 1
    assert logs_a[0].drone_id == "DRONE-A"
    assert len(logs_b) == 1
    assert logs_b[0].drone_id == "DRONE-B"

    # 존재하지 않는 드론 조회 시 빈 리스트 및 None 반환
    assert repo.get_latest("DRONE-NONEXIST") is None
    assert repo.list_by_drone("DRONE-NONEXIST") == []


def test_pin_no_update_or_delete_interface(repo):
    """금기 3(원장 보존): Repository 인터페이스에 update/delete 메서드 부재 기계적 검증."""
    assert not hasattr(repo, "update"), "Repository에 update 메서드 존재 불가 (Append-Only 헌법)"
    assert not hasattr(repo, "delete"), "Repository에 delete 메서드 존재 불가 (Append-Only 헌법)"
    assert not hasattr(repo, "remove"), "Repository에 remove 메서드 존재 불가 (Append-Only 헌법)"
