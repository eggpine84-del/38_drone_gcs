# -*- coding: utf-8 -*-
"""런타임 환경설정 단일 진실 원장 핀-테스트 (Config Pin-Test).

설정 로드, 타입 안전성, 포트/보드레이트 검증 및 싱글톤 무결성 검증.
"""
import pytest
from src.engine.shell.config import AppConfig, get_config, load_config_from_dict, reset_config


def test_1_default_config_loading():
    """환경변수가 주어지지 않았을 때 안전한 기본값으로 로드되는지 검증."""
    cfg = load_config_from_dict({})
    assert cfg.app_env == "development"
    assert cfg.app_host == "0.0.0.0"
    assert cfg.app_port == 8000
    assert cfg.mavlink_enabled is False
    assert cfg.mavlink_connection_string == "udpin:0.0.0.0:14550"
    assert cfg.mavlink_baudrate == 57600
    assert cfg.default_drone_id == "DRONE-01"
    assert cfg.app_db_path == "data/db/app.db"
    assert cfg.heartbeat_timeout_seconds == 3.0
    assert cfg.low_battery_rth_threshold == 15


def test_2_custom_env_dict_type_parsing():
    """문자열 환경변수가 올바른 타입(bool, int, float)으로 파싱되는지 검증."""
    custom_env = {
        "APP_ENV": "production",
        "APP_HOST": "127.0.0.1",
        "APP_PORT": "9000",
        "MAVLINK_ENABLED": "true",
        "MAVLINK_CONNECTION_STRING": "COM4",
        "MAVLINK_BAUDRATE": "115200",
        "DEFAULT_DRONE_ID": "DRONE-ALPHA",
        "APP_DB_PATH": "custom/path.db",
        "HEARTBEAT_TIMEOUT_SECONDS": "5.0",
        "LOW_BATTERY_RTH_THRESHOLD": "20",
    }
    cfg = load_config_from_dict(custom_env)
    assert cfg.app_env == "production"
    assert cfg.app_host == "127.0.0.1"
    assert cfg.app_port == 9000
    assert cfg.mavlink_enabled is True
    assert cfg.mavlink_connection_string == "COM4"
    assert cfg.mavlink_baudrate == 115200
    assert cfg.default_drone_id == "DRONE-ALPHA"
    assert cfg.app_db_path == "custom/path.db"
    assert cfg.heartbeat_timeout_seconds == 5.0
    assert cfg.low_battery_rth_threshold == 20


def test_3_invalid_port_and_baudrate_raises_value_error():
    """유효하지 않은 포트(범위 초과) 및 보드레이트 입력 시 명시적 예외(Fail-Fast) 검증."""
    with pytest.raises(ValueError, match="포트"):
        load_config_from_dict({"APP_PORT": "70000"})

    with pytest.raises(ValueError, match="포트"):
        load_config_from_dict({"APP_PORT": "-1"})

    with pytest.raises(ValueError, match="보드레이트"):
        load_config_from_dict({"MAVLINK_BAUDRATE": "0"})


def test_4_singleton_get_config_integrity():
    """get_config() 싱글톤 인스턴스가 불변 객체로 유지되는지 검증."""
    reset_config()
    cfg1 = get_config()
    cfg2 = get_config()
    assert cfg1 is cfg2
    assert isinstance(cfg1, AppConfig)
