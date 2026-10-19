# -*- coding: utf-8 -*-
"""MAVLink 통신 수신 셸 어댑터 (MAVLink Receiver Shell Adapter).

하드웨어(Serial / UDP) I/O로부터 MAVLink 2.0 패킷을 수신하고,
순수 코어 파서(mavlink_parser_core)를 통해 검증 후 DroneGCSService 단일 원장에 주입합니다.
"""
from datetime import datetime, timezone
import logging
import time
from typing import Any, Dict, List, Optional

from src.engine.core.mavlink_parser_core import (
    convert_mavlink_to_payload,
    resolve_drone_id_from_sysid,
)
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
        auto_detect_sysid: bool = True,
    ) -> None:
        """MAVLink 수신기 초기화.

        Args:
            drone_id: 관제 대상 드론 식별자 (폴백 기본값).
            service: 원장 적재를 총괄하는 GCS 서비스 오케스트레이터.
            connection: 사전 생성된 pymavlink 커넥션 (DI / 테스트 주입용).
            connection_string: UDP 또는 Serial 연결 문자열 (예: 'udpin:0.0.0.0:14550', 'COM3').
            auto_detect_sysid: 패킷 헤더의 SysID 자동 식별 활성화 여부.
        """
        self._drone_id = drone_id.strip() if drone_id else ""
        self._service = service
        self._connection = connection
        self._connection_string = connection_string
        self._auto_detect_sysid = auto_detect_sysid
        self._is_connected = bool(connection)
        self._reconnect_interval: float = 1.0
        self._last_reconnect_attempt: float = 0.0

        # 기체별 최신 상태 격리 캐시 (기체간 상태 섞임 방지)
        self._drone_heartbeats: Dict[str, Dict[str, Any]] = {}
        self._drone_batteries: Dict[str, Dict[str, Any]] = {}

        # 하위 호환 단일 캐시
        self._last_heartbeat: Optional[Dict[str, Any]] = None
        self._last_battery: Optional[Dict[str, Any]] = None

        if self._connection is None and self._connection_string:
            self._init_connection(self._connection_string)

    @property
    def is_connected(self) -> bool:
        """현재 통신 소켓 연결 상태를 반환합니다."""
        return self._is_connected and self._connection is not None

    def _init_connection(self, conn_str: str) -> None:
        """pymavlink 통신 소켓을 연결합니다."""
        try:
            from pymavlink import mavutil
            self._connection = mavutil.mavlink_connection(conn_str)
            self._is_connected = True
            logger.info("MAVLink 연결 성공: %s (기체: %s)", conn_str, self._drone_id)
        except Exception as exc:
            logger.error("MAVLink 연결 실패: %s - 사유: %s", conn_str, str(exc))
            self._connection = None
            self._is_connected = False

    def _handle_disconnect(self) -> None:
        """통신 단절 시 좀비 소켓을 닫고 상태를 재설정합니다."""
        self._is_connected = False
        if self._connection and hasattr(self._connection, "close"):
            try:
                self._connection.close()
            except Exception:
                pass
        self._connection = None
        logger.warning("MAVLink 통신 단절 감지 - 재연결 대기 (기체: %s)", self._drone_id)

    def poll_once(self) -> int:
        """논블로킹 방식으로 가용한 MAVLink 메시지를 1회 순회 소비합니다.

        Returns:
            int: 처리된 텔레메트리 적재 횟수.
        """
        # 1. 미연결 상태 시 재연결 쿨다운 검사 및 조용한 자동 재연결 시도
        if not self.is_connected:
            now = time.time()
            if self._connection_string and (now - self._last_reconnect_attempt >= self._reconnect_interval):
                self._last_reconnect_attempt = now
                self._init_connection(self._connection_string)
            if not self.is_connected:
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

                # SysID 동적 식별 및 기체 ID 결정
                src_sys = getattr(msg, "get_srcSystem", lambda: 0)()
                if self._auto_detect_sysid and (1 <= src_sys <= 255):
                    target_drone_id = resolve_drone_id_from_sysid(src_sys)
                else:
                    target_drone_id = self._drone_id

                if not target_drone_id:
                    continue

                if msg_type == "HEARTBEAT":
                    self._last_heartbeat = msg_dict
                    self._drone_heartbeats[target_drone_id] = msg_dict
                elif msg_type in ("BATTERY_STATUS", "SYS_STATUS"):
                    self._last_battery = msg_dict
                    self._drone_batteries[target_drone_id] = msg_dict
                elif msg_type == "GLOBAL_POSITION_INT":
                    hb = self._drone_heartbeats.get(target_drone_id, self._last_heartbeat)
                    bat = self._drone_batteries.get(target_drone_id, self._last_battery)
                    if hb:
                        now_iso = datetime.now(timezone.utc).isoformat()
                        payload = convert_mavlink_to_payload(
                            drone_id=target_drone_id,
                            gps_msg=msg_dict,
                            heartbeat_msg=hb,
                            battery_msg=bat,
                            timestamp=now_iso,
                        )
                        if payload:
                            result = self._service.process_telemetry(payload)
                            if result.success:
                                processed_count += 1
                                logger.debug("MAVLink 텔레메트리 적재 성공: %s", target_drone_id)
            except (ConnectionError, BrokenPipeError, ConnectionResetError, OSError) as sock_err:
                logger.warning("MAVLink 소켓 에러 감지: %s", str(sock_err))
                self._handle_disconnect()
                break
            except Exception as exc:
                logger.warning("MAVLink 패킷 파싱 예외 발생: %s", str(exc))
                break

        return processed_count

    def close(self) -> None:
        """연결 소켓을 안전하게 닫습니다."""
        self._is_connected = False
        if self._connection and hasattr(self._connection, "close"):
            try:
                self._connection.close()
                logger.info("MAVLink 연결 종료 완료: %s", self._drone_id)
            except Exception as exc:
                logger.warning("MAVLink 연결 닫기 중 예외: %s", str(exc))
        self._connection = None


class MAVLinkMultiReceiver:
    """복수 포트(다중 연결) 및 다중 기체 동시 리스닝 오케스트레이터."""

    def __init__(
        self,
        service: DroneGCSService,
        connections: Optional[List[Any]] = None,
        connection_strings: Optional[List[str]] = None,
        default_drone_id: str = "DRONE-01",
        auto_detect_sysid: bool = True,
    ) -> None:
        """다중 포트 수신기 초기화.

        Args:
            service: GCS 서비스 단일 진실 공급원.
            connections: 사전 생성된 연결 객체 목록 (테스트/DI).
            connection_strings: 연결 문자열 리스트.
            default_drone_id: 폴백 기체 ID.
            auto_detect_sysid: SysID 자동 분류 활성화 여부.
        """
        self._service = service
        self._receivers: List[MAVLinkReceiver] = []

        if connections:
            for conn in connections:
                self._receivers.append(
                    MAVLinkReceiver(
                        drone_id=default_drone_id,
                        service=service,
                        connection=conn,
                        auto_detect_sysid=auto_detect_sysid,
                    )
                )
        elif connection_strings:
            for conn_str in connection_strings:
                self._receivers.append(
                    MAVLinkReceiver(
                        drone_id=default_drone_id,
                        service=service,
                        connection_string=conn_str,
                        auto_detect_sysid=auto_detect_sysid,
                    )
                )

    @property
    def is_connected(self) -> bool:
        """하나 이상의 수신기가 연결되어 있는지 여부를 반환합니다."""
        return any(r.is_connected for r in self._receivers)

    def poll_once(self) -> int:
        """등록된 모든 하위 수신기를 1회 순회 소비하여 총 적재 건수를 반환합니다."""
        total = 0
        for r in self._receivers:
            total += r.poll_once()
        return total

    def close(self) -> None:
        """모든 하위 수신기를 안전하게 회수합니다."""
        for r in self._receivers:
            r.close()

