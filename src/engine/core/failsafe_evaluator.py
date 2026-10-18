# -*- coding: utf-8 -*-
"""페일세이프 판정 순수 코어 (Failsafe Evaluator Core).

CONSTITUTION.md 제1조 3항(위험 격리 및 강제 안전권한) 및 제4조 2항(복합 비상 프로토콜).
외부 I/O 0건, 시간 직접 호출 0건 (Shell 주입 원칙).
"""
from dataclasses import dataclass
from typing import Final

from src.engine.core.drone_state_machine import DroneStatus

DEFAULT_TIMEOUT_SECONDS: Final[float] = 3.0


@dataclass(frozen=True)
class FailsafeEvaluation:
    """페일세이프 판정 결과 봉투 (Pure Output)."""
    is_timeout: bool
    elapsed_seconds: float
    next_status: DroneStatus
    should_transition: bool
    alert_code: str


def evaluate_heartbeat_timeout(
    last_heartbeat_time: float,
    current_time: float,
    current_status: DroneStatus,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> FailsafeEvaluation:
    """하트비트 경과 시간을 순수 계산하여 통신 두절 및 강제 RTH 여부를 판정합니다.

    Args:
        last_heartbeat_time: 직전 하트비트 시각 (에포크 초)
        current_time: 현재 시각 (Shell에서 주입)
        current_status: 현재 비행 상태
        timeout_seconds: 허용 타임아웃 임계치 (기본 3.0초)

    Returns:
        FailsafeEvaluation: 판정 결과 객체
    """
    elapsed = max(0.0, current_time - last_heartbeat_time)

    # 종결(TERMINATED) 상태를 제외하고 3초 이상 미수신 감지 시 강제 RTH 판정
    is_active = current_status != DroneStatus.TERMINATED

    if is_active and elapsed > timeout_seconds:
        should_transition = current_status != DroneStatus.EMERGENCY_RTH
        return FailsafeEvaluation(
            is_timeout=True,
            elapsed_seconds=round(elapsed, 4),
            next_status=DroneStatus.EMERGENCY_RTH,
            should_transition=should_transition,
            alert_code="LOST_HEARTBEAT_TIMEOUT",
        )

    return FailsafeEvaluation(
        is_timeout=False,
        elapsed_seconds=round(elapsed, 4),
        next_status=current_status,
        should_transition=False,
        alert_code="NORMAL",
    )
