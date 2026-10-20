# -*- coding: utf-8 -*-
# [파일명]: test_architecture.py (대장 템플릿 - 아키텍처 핀-테스트 7대 가드)
# [원칙] 소스(src/core, src/shell)와 테스트(tests/test_core, tests/test_shell) 1:1 대칭 분리 및 Zero File Assert 준수
# [SYSTEM] Senior Staff Engineer (Google/Amazon) - Safe, Readable, Scalable Code.
import ast
import os
import pytest


def test_1_config_integrity():
    """① 환경 가드: Config 메모리 로드 및 필수 키 주입 검증"""
    for mod_path in ("src.shell.config", "src.engine.shell.config", "src.engine.config"):
        try:
            mod = __import__(mod_path, fromlist=["get_config"])
            assert mod.get_config() is not None
            return
        except ImportError:
            continue
    pytest.skip("Config 미도입 통과")


NONDETERMINISTIC_CALLS: frozenset[str] = frozenset({
    "datetime.now", "datetime.utcnow", "datetime.today", "date.today",
    "datetime.datetime.now", "datetime.datetime.utcnow", "datetime.datetime.today", "datetime.date.today",
    "time.time", "time.time_ns", "time.monotonic", "time.perf_counter",
    "uuid.uuid1", "uuid.uuid4", "os.urandom",
    # from ... import 구문을 통한 단독 호출 우회 차단
    "now", "utcnow", "today", "time", "time_ns", "monotonic", "perf_counter", "uuid1", "uuid4", "urandom",
})
NONDETERMINISTIC_MODULES: frozenset[str] = frozenset({"random", "secrets", "uuid", "time"})
BANNED_CORE_CALLS: frozenset[str] = frozenset({"open", "os.remove", "os.unlink", "os.makedirs", "os.mkdir"})


def _find_core_dirs(src_root: str = "src") -> list[str]:
    """src/ 하위의 모든 core 및 shared 디렉터리를 구조 무관하게 탐색 (src/core, src/features/*/core, src/shared 등)."""
    found: list[str] = []
    for r, dirs, _ in os.walk(src_root):
        dirs[:] = [d for d in dirs if not d.startswith((".", "__"))]
        if os.path.basename(r) in ("core", "shared"):
            found.append(r)
    return sorted(found)


def _dotted_name(node: ast.AST) -> str:
    """ast.Attribute/ast.Name 체인을 'a.b.c' 문자열로 변환 (그 외는 빈 문자열)."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _dotted_name(node.value)
        return f"{base}.{node.attr}" if base else ""
    return ""


def test_2_pure_core_fcis_separation():
    """② 순수코어 가드: src/ 하위 모든 core(shared 포함) 및 tests/test_core 내 I/O 0건, 시간/난수 직접 호출 0건 AST 검증"""
    banned_modules = {
        "sqlite3", "sqlalchemy", "requests", "httpx", "urllib.request",
        "urllib", "socket", "psycopg2", "aiohttp", "shutil", "subprocess",
    }
    violations = []

    core_dirs = _find_core_dirs() if os.path.exists("src") else []
    if os.path.exists("src"):
        assert core_dirs, (
            "[순수코어 가드 헛돎 차단] src/는 있으나 core 디렉터리를 하나도 찾지 못했습니다. "
            "검사 대상 없이 통과(침묵 폴백)하지 않도록 즉시 실패합니다. 프로젝트 구조를 확인하세요."
        )
    targets = core_dirs + (["tests/test_core"] if os.path.exists("tests/test_core") else [])
    if not targets:
        pytest.skip("src 및 tests/test_core 미도입 프로젝트 통과")

    for target in targets:
        for r, _, files in os.walk(target):
            for f in files:
                if not f.endswith(".py") or f == "test_architecture.py":
                    continue
                fpath = os.path.join(r, f)
                with open(fpath, "r", encoding="utf-8", errors="ignore") as fp:
                    content = fp.read()

                    # test_core 내 물리 파일 I/O 직접 단언 검사 차단
                    if target == "tests/test_core" and any(k in content for k in ["os.path.exists(", "open("]):
                        violations.append((f, "물리 파일 I/O 단언 금지 위반"))

                    # 금지된 외부 I/O 모듈 import 및 비결정적 호출 차단
                    tree = ast.parse(content, filename=f)
                    for n in ast.walk(tree):
                        if isinstance(n, (ast.Import, ast.ImportFrom)):
                            names = [a.name for a in n.names] if isinstance(n, ast.Import) else [n.module or ""]
                            if any(any(m in name for m in banned_modules) for name in names):
                                violations.append((f, "I/O 모듈 import 금지 위반"))
                            if any(name.split(".")[0] in NONDETERMINISTIC_MODULES for name in names):
                                violations.append((f, "난수/시간 모듈 import 금지 위반 (값은 인자로 주입)"))
                        if isinstance(n, ast.Call):
                            call_name = _dotted_name(n.func)
                            if call_name in NONDETERMINISTIC_CALLS:
                                violations.append((f, f"시간/난수 직접 호출 금지 위반: {call_name}() (값은 인자로 주입)"))
                            if call_name in BANNED_CORE_CALLS:
                                violations.append((f, f"코어 내부 직접 파일/OS 조작 금지 위반: {call_name}()"))

    assert not violations, f"순수코어 위반 감지: {violations}"


def test_3_main_orchestration_guard():
    """③ 메인 조율 가드: main.py 내 원시 DB 쿼리/HTML 작성 차단"""
    entry_files = [f for f in ("main.py", "run.py", "src/main.py", "src/engine/main.py") if os.path.exists(f)]
    if not entry_files:
        pytest.skip("main.py 미도입 통과")
    for entry in entry_files:
        with open(entry, "r", encoding="utf-8", errors="ignore") as f:
            content_upper = f.read().upper()
        for kw in ["CREATE TABLE ", "SELECT * FROM ", "SELECT ", "INSERT INTO ", "UPDATE ", "DELETE FROM ", "<HTML", "<BODY"]:
            assert kw not in content_upper, f"{entry} 직접 로직({kw}) 포함 금지"


def test_4_single_adapter_ssot_guard():
    """④ 단일 어댑터 SSoT 가드: 화면(View/UI) 계층에서 저장소 파일 직접 open 차단"""
    if not os.path.exists("src"):
        pytest.skip("src 미도입 통과")
    violations = []
    for r, _, files in os.walk("src"):
        if any(v in r.lower() for v in ["view", "routes", "router", "ui"]):
            for f in files:
                if f.endswith(".py"):
                    fpath = os.path.join(r, f)
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as fp:
                        c = fp.read()
                        if "open('config" in c or 'open("config' in c:
                            violations.append(f)
                        try:
                            tree = ast.parse(c, filename=f)
                            for n in ast.walk(tree):
                                if isinstance(n, ast.Call) and _dotted_name(n.func) in {"open", "sqlite3.connect"}:
                                    violations.append(f"{f}:{n.lineno} ({_dotted_name(n.func)} 직접 호출)")
                        except SyntaxError:
                            continue
    assert not violations, f"화면 계층 파일 직접 open 금지 위반: {violations}"


def _extract_db_identifier(conn) -> str:
    """커넥션에서 물리 파일 경로(SQLite PRAGMA) 또는 DSN 식별자를 추출 (AssertionError 삼킴 방지용)"""
    try:
        cur = conn.cursor()
        cur.execute("PRAGMA database_list;")
        rows = cur.fetchall()
        if rows and len(rows[0]) > 2 and rows[0][2]:
            return os.path.normpath(rows[0][2])
    except Exception:
        pass
    target = getattr(conn, "dsn", "") or str(getattr(conn, "url", ""))
    return os.path.normpath(target) if target else ""


def test_5_db_sandbox_smart_guard(tmp_path):
    """⑤ DB 샌드박스 스마트 가드: 테스트 중 운영 DB 오염 원천 차단 (물리 PRAGMA 실탄 검증 / 범용 다형 지원)."""
    try:
        from src.shell.db_adapter import PROD_DB_PATH, get_active_db_path, get_db_connection
    except ImportError:
        try:
            from src.engine.shell.db_adapter import PROD_DB_PATH, get_active_db_path, get_db_connection
        except ImportError:
            pytest.skip("DB 어댑터 미도입 프로젝트 통과")
            return

    active_path = get_active_db_path()
    assert os.path.normpath(active_path) != os.path.normpath(PROD_DB_PATH), (
        f"[재앙 차단: 테스트 중 운영 DB 직접 참조 감지]\n"
        f"활성 경로: {active_path}\n"
        f"운영 경로: {PROD_DB_PATH}\n"
        f"사유: 테스트 실행 시 운영 DB를 오염시키는 것은 영구 금지됩니다. tests/conftest.py 샌드박스를 확인하세요."
    )

    norm_prod = os.path.normpath(PROD_DB_PATH)

    # 실탄 물리 커넥션 검증 1: 인자 생략 시 결코 운영 DB가 반환되지 않아야 함
    conn = get_db_connection()
    try:
        db_file = _extract_db_identifier(conn)
    finally:
        conn.close()

    if db_file and PROD_DB_PATH:
        assert db_file != norm_prod and norm_prod not in db_file, (
            "get_db_connection이 테스트 중 운영 DB를 반환했습니다."
        )

    # 실탄 물리 커넥션 검증 2: PROD_DB_PATH 인자 강제 전달 시에도 샌드박스로 우회되어야 함
    conn_override = get_db_connection(PROD_DB_PATH)
    try:
        db_file_override = _extract_db_identifier(conn_override)
    finally:
        conn_override.close()

    if db_file_override and PROD_DB_PATH:
        assert db_file_override != norm_prod and norm_prod not in db_file_override, (
            "PROD_DB_PATH 인자 전달 시 샌드박스 강제 전향에 실패했습니다."
        )


def test_6_shell_blackbox_contract_guard():
    """⑥ 블랙박스 계약 가드: test_shell 내 내부 데이터/설정 파일 직접 단언 차단 (블랙박스 API 호출 원칙)"""
    if not os.path.exists("tests/test_shell"):
        pytest.skip("test_shell 미도입 통과")
    violations = []
    for r, _, files in os.walk("tests/test_shell"):
        for f in files:
            if f.endswith(".py") and "architecture" not in f:
                with open(os.path.join(r, f), "r", encoding="utf-8", errors="ignore") as fp:
                    c = fp.read()
                    for forbidden in [".ini", ".conf", ".cfg", "data/"]:
                        if "exists(" in c and forbidden in c:
                            violations.append((f, forbidden))
    assert not violations, f"test_shell 블랙박스 계약 위반 (물리 파일 직접 단언): {violations}"


def test_7_ui_template_line_guard():
    """⑦ UI 템플릿 가드: HTML 파일 300줄 한도 엄수 및 조각 템플릿 분리 검증"""
    if not os.path.exists("src"):
        pytest.skip("src 미도입 통과")
    violations = []
    limit = 300
    for r, _, files in os.walk("src"):
        for f in files:
            if f.endswith(".html"):
                fpath = os.path.join(r, f)
                with open(fpath, "r", encoding="utf-8", errors="ignore") as fp:
                    lines = len(fp.readlines())
                    if lines > limit:
                        violations.append(f"{f} ({lines}줄 > {limit}줄 한도)")
    assert not violations, (
        f"[UI 아키텍처 위반: 300줄 초과 HTML 감지] {violations}\n"
        f"철칙: 억지 줄바꿈 축소 절대 금지. 즉시 [refactor 모드]로 전환하여 components/ 조각 템플릿으로 분리하세요."
    )
