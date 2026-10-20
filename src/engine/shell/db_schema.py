# -*- coding: utf-8 -*-
# [파일명]: db_schema.py (대장 템플릿 - 데이터베이스 스키마 및 초기 시드 전담 금고)
# [원칙] 1. P1 스키마 헌법(4대 메타컬럼/PK) | 2. 100% 멱등 DDL(CREATE TABLE IF NOT EXISTS) | 3. 기 존재 데이터 영구 보존
# [SYSTEM] Senior Staff Engineer (Google/Amazon) - Safe, Readable, Scalable Code.
import os
import sqlite3
from typing import Optional


def init_db(db_path: Optional[str] = None) -> None:
    """테이블 스키마 생성 및 초기 시드 데이터 멱등 삽입 (DDL 금고 전담)."""
    # 단일 커넥션 팩토리 동적 바인딩
    try:
        from src.engine.shell.db_adapter import get_db_connection
    except ImportError:
        import sys
        current_dir = os.path.dirname(os.path.abspath(__file__))
        if current_dir not in sys.path:
            sys.path.insert(0, current_dir)
        from db_adapter import get_db_connection

    conn = get_db_connection(db_path)
    cur = conn.cursor()

    # 1. 범용 기본 테이블: 4대 메타 컬럼(id, created_at, updated_at, is_deleted) 준수
    cur.execute("""
    CREATE TABLE IF NOT EXISTS items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        is_active INTEGER NOT NULL DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        is_deleted INTEGER NOT NULL DEFAULT 0
    );
    """)

    # 2. 멱등 컬럼 마이그레이션 표준 (SQLite / PostgreSQL 공통 호환: 기존 운영 DB 무중단 확장)
    try:
        cur.execute("ALTER TABLE items ADD COLUMN description TEXT NOT NULL DEFAULT '';")
    except Exception as exc:
        import logging
        logging.getLogger(__name__).debug("컬럼 마이그레이션 스킵(이미 존재): %s", str(exc))

    # 3. 멱등 초기 시드 데이터 주입 (기존 데이터 존재 시 스킵)
    cur.execute("SELECT COUNT(*) FROM items WHERE is_deleted = 0;")
    if cur.fetchone()[0] == 0:
        cur.execute("""
        INSERT INTO items (name, description, is_active)
        VALUES ('기본 아이템', '초기 부팅 시 생성된 템플릿 아이템입니다.', 1);
        """)

    # 4. 드론 텔레메트리 블랙박스 원장 테이블 (CONSTITUTION 제2조 및 4대 공리 영구보존)
    cur.execute(
        "CREATE TABLE IF NOT EXISTS telemetry_logs ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "drone_id TEXT NOT NULL, "
        "latitude REAL NOT NULL, "
        "longitude REAL NOT NULL, "
        "altitude REAL NOT NULL, "
        "speed REAL NOT NULL, "
        "battery INTEGER NOT NULL, "
        "status TEXT NOT NULL, "
        "timestamp TEXT NOT NULL, "
        "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);"
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_telemetry_drone_time "
        "ON telemetry_logs (drone_id, timestamp);"
    )

    conn.commit()
    conn.close()


if __name__ == "__main__":
    print("= [db_schema.py] 단독 스키마 생성 및 시드 검증 =")
    test_db = "temp_schema_test.db"
    try:
        init_db(test_db)
        print("  -> init_db() 멱등 스키마 생성 및 초기 시드 주입 성공!")
    finally:
        if os.path.exists(test_db):
            os.remove(test_db)
