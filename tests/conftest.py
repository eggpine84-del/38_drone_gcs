# -*- coding: utf-8 -*-
# [파일명]: conftest.py (대장 템플릿 - 테스트 러너 전역 샌드박스 격리)
# [원칙] 테스트 러너 전역 샌드박스 격리 (운영 DB 절대 보호)
# [SYSTEM] Senior Staff Engineer (Google/Amazon) - Safe, Readable, Scalable Code.
import os
import pytest


@pytest.fixture(autouse=True, scope="function")
def enforce_test_db_sandbox(tmp_path):
    """각 테스트마다 격리된 임시 샌드박스를 강제 바인딩 (운영 DB 오염 원천 차단)."""
    test_db_path = str(tmp_path / "sandbox_app.db")
    os.environ["APP_ENV"] = "test"
    os.environ["DATABASE_URL"] = f"sqlite:///{test_db_path}"
    os.environ["APP_DB_PATH"] = test_db_path

    # DB 스키마 동적 초기화 (db_schema 금고 우선 탐색 및 레거시 어댑터 폴백)
    for mod_path in [
        "src.engine.shell.db_schema",
        "src.engine.shell.db_adapter",
        "src.shell.db_schema",
        "src.shell.db_adapter",
    ]:
        try:
            mod = __import__(mod_path, fromlist=["init_db"])
            if hasattr(mod, "init_db"):
                mod.init_db(test_db_path)
                break
        except ImportError:
            pass

    yield test_db_path

    for env_key in ["DATABASE_URL", "APP_ENV", "APP_DB_PATH"]:
        if env_key in os.environ:
            del os.environ[env_key]
