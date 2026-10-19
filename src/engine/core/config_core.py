# -*- coding: utf-8 -*-
"""설정 순수 코어 검증기 (Config Pure Core).

FCIS 헌법 준수: 외부 I/O 0건, Side-Effect 0건, 0.001초 결정론적 연산.
포트, 보드레이트, 타임아웃, 임계치 등의 유효성을 검증합니다.
"""
from typing import Tuple


def validate_config_invariants(
    app_port: int,
    mavlink_baudrate: int,
    heartbeat_timeout_seconds: float,
    low_battery_rth_threshold: int,
) -> Tuple[str, ...]:
    """설정값들의 불변량(Invariants)을 순수 검증하고 위반 사유 튜플을 반환합니다.

    Args:
        app_port: 웹 서버 포트 번호.
        mavlink_baudrate: 시리얼 통신 보드레이트.
        heartbeat_timeout_seconds: 하트비트 두절 판정 시간(초).
        low_battery_rth_threshold: 비상 귀환 배터리 임계치(%).

    Returns:
        Tuple[str, ...]: 감지된 위반 사항 식별자 튜플.
    """
    violations = []

    # 1. 포트 번호 검증 (1 ~ 65535)
    if not (1 <= app_port <= 65535):
        violations.append("INVALID_PORT_RANGE")

    # 2. 보드레이트 양수 검증
    if mavlink_baudrate <= 0:
        violations.append("INVALID_BAUDRATE")

    # 3. 타임아웃 양수 검증
    if heartbeat_timeout_seconds <= 0.0:
        violations.append("INVALID_TIMEOUT")

    # 4. 배터리 임계치 범위 (1 ~ 99)
    if not (1 <= low_battery_rth_threshold <= 99):
        violations.append("INVALID_BATTERY_THRESHOLD")

    return tuple(violations)
