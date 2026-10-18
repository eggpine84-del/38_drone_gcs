# -*- coding: utf-8 -*-
# [파일명]: db_adapter.py (대장 템플릿 - 데이터베이스 어댑터 Shell용)
# [원칙] 1. SQLite 3대 헌법(WAL/외래키/5초대기) | 2. 테스트 러너 감지 시 운영 DB 접근 100% 차단 | 3. 100% 멱등 DDL
# [SYSTEM] Senior Staff Engineer (Google/Amazon) - Safe, Readable, Scalable Code.
import os
import sys
import sqlite3
from typing import Any, Dict, List, Optional

# [1. 경로 헌법 구역]: 운영 DB 기본 경로 및 환경변수 오버라이드
PROD_DB_PATH = os.path.join("data", "db", "app.db")


def get_active_db_path() -> str:
    """테스트/운영 환경 감지 기반 활성 DB 경로 반환 (테스트 중 운영 DB 접근 원천 차단)."""
    # 1. 명시적 지정 경로 최우선 (테스트 임시 샌드박스 등)
    env_db = os.getenv("APP_DB_PATH")
    if env_db:
        return env_db
    # 2. 테스트 환경 감지 시 운영 DB 차단 및 인메모리 격리
    if os.getenv("APP_ENV") == "test" or "pytest" in sys.modules:
        return ":memory:"
    # 3. 실제 운영 경로 반환
    return PROD_DB_PATH


DEFAULT_DB_PATH = PROD_DB_PATH


# [2. 커넥션 헌법 구역]: SQLite 3대 헌법 강제 커넥션 팩토리
def get_db_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """SQLite 3대 헌법(WAL, foreign_keys=ON, busy_timeout=5000) 적용 커넥션 반환."""
    # 테스트 환경 안전 가드
    if os.getenv("APP_ENV") == "test" or "pytest" in sys.modules:
        target_path = get_active_db_path() if (db_path is None or db_path == PROD_DB_PATH) else db_path
    else:
        target_path = db_path if db_path is not None else get_active_db_path()

    if target_path != ":memory:" and os.path.dirname(target_path):
        os.makedirs(os.path.dirname(target_path), exist_ok=True)

    conn = sqlite3.connect(target_path, timeout=5.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA busy_timeout = 5000;")
    return conn


# [3. 범용 쿼리 헌법 구역]: 단 1줄 종결 + 100% 자원 자동 해제(Leak-Free) 2대 만능 헬퍼
def execute_query(sql: str, params: tuple = (), db_path: Optional[str] = None, conn: Optional[sqlite3.Connection] = None) -> List[Dict[str, Any]]:
    """안전한 SELECT 조회 헬퍼 (100% 파라미터화 바인딩 & 커넥션 자동 회수)."""
    close_needed = False
    if conn is None:
        conn = get_db_connection(db_path)
        close_needed = True
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        return [dict(r) for r in cur.fetchall()]
    finally:
        if close_needed:
            conn.close()


def execute_command(sql: str, params: tuple = (), db_path: Optional[str] = None, conn: Optional[sqlite3.Connection] = None) -> int:
    """안전한 INSERT/UPDATE/DELETE 헬퍼 (트랜잭션 커밋 & lastrowid/rowcount 반환 & 커넥션 자동 회수)."""
    close_needed = False
    if conn is None:
        conn = get_db_connection(db_path)
        close_needed = True
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        conn.commit()
        return cur.lastrowid if cur.lastrowid else cur.rowcount
    finally:
        if close_needed:
            conn.close()


if __name__ == "__main__":
    print("= [db_adapter.py] 단독 동작 테스트 =")
    test_db = "temp_boilerplate_test.db"
    try:
        # 순수 배관 동작 확인: 임시 테이블 생성 및 2대 만능 헬퍼 검증
        execute_command("CREATE TABLE IF NOT EXISTS _test (id INTEGER PRIMARY KEY, val TEXT);", db_path=test_db)
        row_id = execute_command("INSERT INTO _test (val) VALUES (?);", ("테스트_데이터",), db_path=test_db)
        print(f"  -> execute_command 삽입 성공! (생성 ID: {row_id})")

        rows = execute_query("SELECT * FROM _test WHERE id = ?;", (row_id,), db_path=test_db)
        assert len(rows) == 1 and rows[0]["val"] == "테스트_데이터", "단독 검증 실패"
        print(f"  -> execute_query 조회 성공! (가져온 데이터: {rows[0]['val']})")

        print("  -> SQLite 3대 헌법 및 만능 배관 헬퍼 가동 성공!")
    finally:
        if os.path.exists(test_db):
            os.remove(test_db)

