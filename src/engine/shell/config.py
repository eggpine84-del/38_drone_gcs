# -*- coding: utf-8 -*-
"""런타임 환경설정 단일 진실 원장 셸 (Runtime AppConfig Shell).

.env 파일 및 OS 환경변수를 통합하여 불변 AppConfig 싱글톤을 제공합니다.
"""
from dataclasses import dataclass
import os
from typing import Any, Mapping, Optional

from dotenv import dotenv_values

from src.engine.core.config_core import validate_config_invariants


@dataclass(frozen=True)
class AppConfig:
    """시스템 런타임 환경설정 불변 단일 진실 원장 (SSOT)."""
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    mavlink_enabled: bool = False
    mavlink_connection_string: str = "udpin:0.0.0.0:14550"
    mavlink_baudrate: int = 57600
    default_drone_id: str = "DRONE-01"
    app_db_path: str = "data/db/app.db"
    log_level: str = "INFO"
    heartbeat_timeout_seconds: float = 3.0
    low_battery_rth_threshold: int = 15
    max_altitude_limit: float = 150.0


def _parse_bool(val: Any, default: bool = False) -> bool:
    """문자열을 불리언으로 파싱합니다."""
    if val is None:
        return default
    if isinstance(val, bool):
        return val
    return str(val).strip().lower() in ("true", "1", "yes", "y", "on")


def load_config_from_dict(env_map: Mapping[str, Any]) -> AppConfig:
    """환경변수 맵으로부터 검증된 AppConfig 불변 객체를 생성합니다."""
    app_env = str(env_map.get("APP_ENV", "development")).strip()
    app_host = str(env_map.get("APP_HOST", "0.0.0.0")).strip()

    try:
        app_port = int(env_map.get("APP_PORT", 8000))
    except (ValueError, TypeError):
        raise ValueError("유효하지 않은 포트 번호입니다 (정수 필수).")

    mavlink_enabled = _parse_bool(env_map.get("MAVLINK_ENABLED", False))
    mavlink_conn = str(env_map.get("MAVLINK_CONNECTION_STRING", "udpin:0.0.0.0:14550")).strip()

    try:
        mavlink_baud = int(env_map.get("MAVLINK_BAUDRATE", 57600))
    except (ValueError, TypeError):
        raise ValueError("유효하지 않은 보드레이트입니다 (정수 필수).")

    default_drone = str(env_map.get("DEFAULT_DRONE_ID", "DRONE-01")).strip()
    app_db_path = str(env_map.get("APP_DB_PATH", "data/db/app.db")).strip()
    log_level = str(env_map.get("LOG_LEVEL", "INFO")).strip().upper()

    try:
        hb_timeout = float(env_map.get("HEARTBEAT_TIMEOUT_SECONDS", 3.0))
    except (ValueError, TypeError):
        hb_timeout = 3.0

    try:
        low_bat = int(env_map.get("LOW_BATTERY_RTH_THRESHOLD", 15))
    except (ValueError, TypeError):
        low_bat = 15

    try:
        max_alt = float(env_map.get("MAX_ALTITUDE_LIMIT", 150.0))
    except (ValueError, TypeError):
        max_alt = 150.0

    # 순수 코어 불변량 검증
    violations = validate_config_invariants(
        app_port=app_port,
        mavlink_baudrate=mavlink_baud,
        heartbeat_timeout_seconds=hb_timeout,
        low_battery_rth_threshold=low_bat,
    )

    if "INVALID_PORT_RANGE" in violations:
        raise ValueError(f"유효하지 않은 포트 범위입니다: {app_port} (1~65535)")
    if "INVALID_BAUDRATE" in violations:
        raise ValueError(f"유효하지 않은 보드레이트 값입니다: {mavlink_baud} (>0)")
    if violations:
        raise ValueError(f"설정 불변량 위반 감지: {violations}")

    return AppConfig(
        app_env=app_env,
        app_host=app_host,
        app_port=app_port,
        mavlink_enabled=mavlink_enabled,
        mavlink_connection_string=mavlink_conn,
        mavlink_baudrate=mavlink_baud,
        default_drone_id=default_drone,
        app_db_path=app_db_path,
        log_level=log_level,
        heartbeat_timeout_seconds=hb_timeout,
        low_battery_rth_threshold=low_bat,
        max_altitude_limit=max_alt,
    )


_CACHED_CONFIG: Optional[AppConfig] = None


def get_config() -> AppConfig:
    """시스템 전역 단일 진실 원장 AppConfig 싱글톤 반환."""
    global _CACHED_CONFIG
    if _CACHED_CONFIG is None:
        merged_env: dict = {}
        # 1. .env 파일 로드 (있을 경우)
        if os.path.exists(".env"):
            merged_env.update(dotenv_values(".env"))
        # 2. OS 환경변수 덮어쓰기
        merged_env.update(os.environ)
        _CACHED_CONFIG = load_config_from_dict(merged_env)
    return _CACHED_CONFIG


def reset_config() -> None:
    """테스트용 설정 캐시 초기화."""
    global _CACHED_CONFIG
    _CACHED_CONFIG = None
