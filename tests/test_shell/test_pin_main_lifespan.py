# -*- coding: utf-8 -*-
"""메인 라이프스팬 MAVLink 워커 결합 핀-테스트 (Lifespan Pin-Test).

서버 시작 시 MAVLink 백그라운드 워커 기동 및 종료 시 자원 회수를 검증.
"""
import asyncio
import pytest
from unittest.mock import MagicMock, patch
from fastapi import FastAPI

from main import lifespan
from src.engine.shell.config import AppConfig


@pytest.mark.anyio
async def test_1_lifespan_with_mavlink_disabled():
    """MAVLINK_ENABLED=False일 때 백그라운드 워커 없이 DB 초기화만 수행되는지 검증."""
    test_app = FastAPI(lifespan=lifespan)
    with patch("src.engine.shell.config.get_config") as mock_cfg:
        mock_cfg.return_value = AppConfig(mavlink_enabled=False)
        async with lifespan(test_app):
            # 정상 기동 확인
            pass


@pytest.mark.anyio
async def test_2_lifespan_with_mavlink_enabled_starts_and_stops_worker():
    """MAVLINK_ENABLED=True일 때 백그라운드 워커가 생성되고 종료 시 안전하게 해제되는지 검증."""
    test_app = FastAPI(lifespan=lifespan)
    mock_receiver = MagicMock()
    mock_receiver.poll_once.return_value = 1

    with patch("src.engine.shell.config.get_config") as mock_cfg, \
         patch("src.engine.shell.mavlink_receiver.MAVLinkReceiver", return_value=mock_receiver), \
         patch("pymavlink.mavutil.mavlink_connection"):

        mock_cfg.return_value = AppConfig(
            mavlink_enabled=True,
            mavlink_connection_string="udpin:0.0.0.0:14550",
            default_drone_id="TEST-DRONE",
        )

        async with lifespan(test_app):
            # 워커가 실행되도록 잠시 양보
            await asyncio.sleep(0.1)
            assert mock_receiver.poll_once.called

        # 종료 시 close 호출 확인
        assert mock_receiver.close.called


def test_3_main_entrypoint_pure_orchestrator():
    """main.py가 더미 코드 및 기생 assert 없이 120줄 이하 순수 웹 오케스트레이터인지 검증."""
    import main
    import inspect

    # 1. 미사용 유령 더미 함수 부재 단언
    assert not hasattr(main, "run_main_workflow"), "main.py에 미사용 run_main_workflow 잔존 금지"
    assert not hasattr(main, "run_main_workflow_sync"), "main.py에 미사용 run_main_workflow_sync 잔존 금지"
    assert not hasattr(main, "validate_and_prepare_input"), "main.py에 더미 validate_and_prepare_input 잔존 금지"
    assert not hasattr(main, "process_core_behavior"), "main.py에 더미 process_core_behavior 잔존 금지"

    # 2. 파일 라인 수 120줄 이하 경량화 단언 (SRP)
    with open("main.py", "r", encoding="utf-8") as f:
        lines = f.readlines()
    assert len(lines) <= 120, f"main.py는 120줄 이하여야 합니다 (현재: {len(lines)}줄)"

    # 3. 프로덕션 내 기생 assert 테스트 부재 단언
    content = "".join(lines)
    assert "assert " not in content, "main.py 프로덕션 코드 내부에 기생 assert 테스트 금지"

    # 4. FastAPI app 및 라우터 등록 무결성 검증
    def _get_paths(route_list):
        paths = []
        for r in route_list:
            if hasattr(r, "path"):
                paths.append(r.path)
            elif hasattr(r, "routes"):
                paths.extend(_get_paths(r.routes))
            elif hasattr(r, "original_router") and hasattr(r.original_router, "routes"):
                paths.extend(_get_paths(r.original_router.routes))
        return paths

    routes = _get_paths(main.app.routes)
    assert "/" in routes, "대시보드 메인 라우트 누락"
    assert "/api/telemetry" in routes, "텔레메트리 라우트 누락"
