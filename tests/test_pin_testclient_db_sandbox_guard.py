# -*- coding: utf-8 -*-
# [파일명]: test_pin_testclient_db_sandbox_guard.py
# [목적]: TestClient 및 unittest 등 비정규 테스트 실행 시 운영 DB 접근 차단 가드 검증
import os


def test_pin_db_adapter_sandbox_components_exist():
    """db_adapter 모듈에 _TEST_MODULES, _FALLBACK_SANDBOX_DB, _is_test_mode 3대 보호회로 부품이 선언되어 있는지 검증 (Red 선행)."""
    import src.engine.shell.db_adapter as adapter

    assert hasattr(adapter, "_TEST_MODULES"), "보호회로 결함: _TEST_MODULES가 선언되지 않음!"
    assert hasattr(adapter, "_FALLBACK_SANDBOX_DB"), "보호회로 결함: _FALLBACK_SANDBOX_DB가 선언되지 않음!"
    assert hasattr(adapter, "_is_test_mode"), "보호회로 결함: _is_test_mode 함수가 선언되지 않음!"
    assert "fastapi.testclient" in adapter._TEST_MODULES
    assert "starlette.testclient" in adapter._TEST_MODULES
    assert "unittest" in adapter._TEST_MODULES


def test_pin_testclient_blocks_prod_db():
    """fastapi.testclient 또는 starlette.testclient 로드 시 운영 DB가 차단되는지 검증."""
    import fastapi.testclient  # noqa: F401
    from src.engine.shell.db_adapter import PROD_DB_PATH, get_active_db_path

    active = get_active_db_path()
    assert active != PROD_DB_PATH, f"재앙 차단: TestClient 환경에서 운영 DB({PROD_DB_PATH})가 반환됨!"


def test_pin_unittest_blocks_prod_db():
    """unittest 로드 시 운영 DB가 차단되는지 검증."""
    import unittest  # noqa: F401
    from src.engine.shell.db_adapter import PROD_DB_PATH, get_active_db_path

    active = get_active_db_path()
    assert active != PROD_DB_PATH, f"재앙 차단: unittest 환경에서 운영 DB({PROD_DB_PATH})가 반환됨!"
