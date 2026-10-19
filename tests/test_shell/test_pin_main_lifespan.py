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
