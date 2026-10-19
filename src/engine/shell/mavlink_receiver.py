# -*- coding: utf-8 -*-
"""MAVLink 통신 수신 셸 어댑터 (MAVLink Receiver Shell Adapter).

하드웨어(Serial / UDP) I/O로부터 MAVLink 2.0 패킷을 수신하고,
순수 코어 파서(mavlink_parser_core)를 통해 검증 후 DroneGCSService 단일 원장에 주입합니다.
"""
from datetime import datetime, timezone
import logging
from typing import Any, Dict, Optional

from src.engine.core.mavlink_parser_core import convert_mavlink_to_payload
from src.engine.shell.drone_gcs_service import DroneGCSService

logger = logging.getLogger(__name__)


class MAVLinkReceiver:
    """MAVLink 2.0 하드웨어 통신 수신 어댑터."""

    def __init__(
        self,
        drone_id: str,
        service: DroneGCSService,
        connection: Any = None,
        connection_string: Optional[str] = None,
    ) -> None:
        """MAVLink 수신기 초기화.

        Args:
            drone_id: 관제 대상 드론 식별자.
            service: 원장 적재를 총괄하는 GCS 서비스 오케스트레이터.
            connection: 사전 생성된 pymavlink 커넥션 (DI / 테스트 주입용).
            connection_string: UDP 또는 Serial 연결 문자열 (예: 'udpin:0.0.0.0:14550', 'COM3').
        """
        self._drone_id = drone_id.strip() if drone_id else ""
        self._service = service
        self._connection = connection
        self._connection_string = connection_string

        # 내부 메시지 캐시 (기체별 최신 상태 유지)
        self._last_heartbeat: Optional[Dict[str, Any]] = None
        self._last_battery: Optional[Dict[str, Any]] = None

        if self._connection is None and self._connection_string:
            self._init_connection(self._connection_string)

    def _init_connection(self, conn_str: str) -> None:
        """pymavlink 통신 소켓을 연결합니다."""
        try:
            from pymavlink import mavutil
            self._connection = mavutil.mavlink_connection(conn_str)
            logger.info("MAVLink 연결 성공: %s (기체: %s)", conn_str, self._drone_id)
        except Exception as exc:
            logger.error("MAVLink 연결 실패: %s - 사유: %s", conn_str, str(exc))
            self._connection = None

    def poll_once(self) -> int:
        """논블로킹 방식으로 가용한 MAVLink 메시지를 1회 순회 소비합니다.

        Returns:
            int: 처리된 텔레메트리 적재 횟수.
        """
        if not self._connection or not self._drone_id:
            return 0

        processed_count = 0

        while True:
            try:
                # recv_msg()는 논블로킹으로 수신 큐의 메시지를 반환
                msg = self._connection.recv_msg()
                if msg is None:
                    break

                msg_type = msg.get_type()
                msg_dict = msg.to_dict() if hasattr(msg, "to_dict") else {}

                if msg_type == "HEARTBEAT":
                    self._last_heartbeat = msg_dict
                elif msg_type in ("BATTERY_STATUS", "SYS_STATUS"):
                    self._last_battery = msg_dict
                elif msg_type == "GLOBAL_POSITION_INT":
                    if self._last_heartbeat:
                        now_iso = datetime.now(timezone.utc).isoformat()
                        payload = convert_mavlink_to_payload(
                            drone_id=self._drone_id,
                            gps_msg=msg_dict,
                            heartbeat_msg=self._last_heartbeat,
                            battery_msg=self._last_battery,
                            timestamp=now_iso,
                        )
                        if payload:
                            result = self._service.process_telemetry(payload)
                            if result.success:
                                processed_count += 1
                                logger.debug("MAVLink 텔레메트리 적재 성공: %s", self._drone_id)
            except Exception as exc:
                logger.warning("MAVLink 패킷 파싱 예외 발생: %s", str(exc))
                break

        return processed_count

    def close(self) -> None:
        """연결 소켓을 안전하게 닫습니다."""
        if self._connection and hasattr(self._connection, "close"):
            try:
                self._connection.close()
                logger.info("MAVLink 연결 종료 완료: %s", self._drone_id)
            except Exception as exc:
                logger.warning("MAVLink 연결 닫기 중 예외: %s", str(exc))
