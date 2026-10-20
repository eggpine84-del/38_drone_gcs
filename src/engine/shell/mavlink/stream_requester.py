# -*- coding: utf-8 -*-
# [파일명]: stream_requester.py
# [목적]: FCU 대상 GCS 하트비트 및 5대 텔레메트리 스트림 전송 능동 요청 전담 헬퍼 (Egress)
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


def send_gcs_heartbeat_and_stream_request(
    connection: Any,
    last_heartbeat_sent: float,
    heartbeat_interval: float = 1.0,
) -> float:
    """FCU로 GCS 하트비트 및 전체 텔레메트리 스트림 전송을 능동적으로 요청합니다.

    ArduPilot/PX4는 GCS의 하트비트 및 데이터 스트림 요청이 없으면
    대역폭 절약을 위해 텔레메트리 스트림을 개방하지 않으므로 자립적 송출이 필수적입니다.

    Returns:
        float: 갱신된 마지막 하트비트 전송 시각
    """
    if not connection:
        return last_heartbeat_sent

    mav = getattr(connection, "mav", None)
    if not mav:
        return last_heartbeat_sent

    now = time.time()
    if (now - last_heartbeat_sent) < heartbeat_interval:
        return last_heartbeat_sent

    # 1. GCS 하트비트 송출 (MAV_TYPE_GCS=6, MAV_AUTOPILOT_INVALID=8)
    if hasattr(mav, "heartbeat_send"):
        try:
            mav.heartbeat_send(
                6,  # MAV_TYPE_GCS
                8,  # MAV_AUTOPILOT_INVALID
                0,  # base_mode
                0,  # custom_mode
                0,  # system_status
            )
        except Exception as exc:
            logger.debug("GCS 하트비트 송신 예외 무시: %s", str(exc))

    # 2. 데이터 스트림 요청 송출 (ArduPilot 침묵 방어를 위한 5대 스트림 전수 개방)
    if hasattr(mav, "request_data_stream_send"):
        try:
            target_sys = getattr(connection, "target_system", 1) or 1
            target_comp = getattr(connection, "target_component", 1) or 1
            # 0: ALL, 6: POSITION(GLOBAL_POSITION_INT), 2: EXTENDED_STATUS, 10: EXTRA1, 11: EXTRA2
            for s_id in (0, 6, 2, 10, 11):
                mav.request_data_stream_send(
                    target_sys,
                    target_comp,
                    s_id,
                    4,  # 4Hz
                    1,  # start
                )
        except Exception as exc:
            logger.debug("데이터 스트림 요청 송신 예외 무시: %s", str(exc))

    return now
