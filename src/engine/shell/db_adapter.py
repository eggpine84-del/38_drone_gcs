# [파일명]: db_adapter.py (대장 템플릿 - 데이터베이스 어댑터 Shell용)
# [원칙] 1. SQLite 3대 헌법(WAL/외래키/5초대기) | 2. 테스트 러너 감지 시 운영 DB 접근 100% 차단 | 3. 100% 멱등 DDL
# [SYSTEM] Senior Staff Engineer (Google/Amazon) - Safe, Readable, Scalable Code.
import os
import sqlite3
import sys
import tempfile
from typing import Any

# [1. 경로 헌법 구역]: 운영 DB 기본 경로 및 비정규 테스트 차단 샌드박스
PROD_DB_PATH = os.path.join("data", "db", "app.db")
_TEST_MODULES = ("pytest", "unittest", "fastapi.testclient", "starlette.testclient")
_FALLBACK_SANDBOX_DB = os.path.join(tempfile.gettempdir(), "pytest_sandbox_fallback.db")


def _is_test_mode() -> bool:
    """pytest, unittest, TestClient 단독 호출 등 모든 비정규 테스트 실행을 감지합니다."""
    if os.getenv("APP_ENV") == "test":
        return True
    return any(mod in sys.modules for mod in _TEST_MODULES)


def _clean_sqlite_path(raw_path: str) -> str:
    """sqlite:/// URL 접두사를 순수 파일 시스템 경로로 정규화."""
    prefix = "sqlite:///"
    is_url = raw_path.startswith(prefix)
    return raw_path[len(prefix) :] if is_url else raw_path


def get_active_db_path() -> str:
    """테스트/운영 환경 감지 기반 활성 DB 경로 반환 (테스트 중 운영 DB 접근 원천 차단)."""
    # 1. 일반 운영 환경일 때는 운영 DB 경로 반환
    if not _is_test_mode():
        return os.getenv("APP_DB_PATH") or PROD_DB_PATH

    # 2. 테스트 환경일 때는 어떠한 경우에도 운영 DB 접근 금지 (강제 임시 샌드박스 격리)
    raw_env = (
        os.getenv("APP_DB_PATH")
        or os.getenv("TEST_DB_PATH")
        or os.getenv("DATABASE_URL")
    )
    candidate = _clean_sqlite_path(raw_env) if raw_env else ""
    is_safe = bool(
        candidate and os.path.normpath(candidate) != os.path.normpath(PROD_DB_PATH)
    )
    return candidate if is_safe else _FALLBACK_SANDBOX_DB


DEFAULT_DB_PATH = PROD_DB_PATH


# [2. 커넥션 헌법 구역]: SQLite 3대 헌법 강제 커넥션 팩토리
def get_db_connection(db_path: str | None = None) -> sqlite3.Connection:
    """SQLite 3대 헌법(WAL, foreign_keys=ON, busy_timeout=5000) 적용 커넥션 반환."""
    # 테스트 환경 안전 가드
    if _is_test_mode():
        target_path = (
            get_active_db_path()
            if (
                db_path is None
                or os.path.normpath(db_path) == os.path.normpath(PROD_DB_PATH)
            )
            else db_path
        )
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
def execute_query(
    sql: str,
    params: tuple = (),
    db_path: str | None = None,
    conn: sqlite3.Connection | None = None,
) -> list[dict[str, Any]]:
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


def execute_command(
    sql: str,
    params: tuple = (),
    db_path: str | None = None,
    conn: sqlite3.Connection | None = None,
) -> int:
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
        execute_command(
            "CREATE TABLE IF NOT EXISTS _test (id INTEGER PRIMARY KEY, val TEXT);",
            db_path=test_db,
        )
        row_id = execute_command(
            "INSERT INTO _test (val) VALUES (?);", ("테스트_데이터",), db_path=test_db
        )
        print(f"  -> execute_command 삽입 성공! (생성 ID: {row_id})")

        rows = execute_query(
            "SELECT * FROM _test WHERE id = ?;", (row_id,), db_path=test_db
        )
        assert len(rows) == 1 and rows[0]["val"] == "테스트_데이터", "단독 검증 실패"
        print(f"  -> execute_query 조회 성공! (가져온 데이터: {rows[0]['val']})")

        print("  -> SQLite 3대 헌법 및 만능 배관 헬퍼 가동 성공!")
    finally:
        if os.path.exists(test_db):
            os.remove(test_db)
