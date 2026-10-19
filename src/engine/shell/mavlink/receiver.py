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
        self._last_heartbeat_sent: float = 0.0
        self._heartbeat_interval: float = 1.0

        # 기체별 최신 상태 격리 캐시 (기체간 상태 섞임 방지)
        self._drone_heartbeats: Dict[str, Dict[str, Any]] = {}
        self._drone_batteries: Dict[str, Dict[str, Any]] = {}
        self._drone_last_gps: Dict[str, Dict[str, Any]] = {}
        self._drone_last_ingest_time: Dict[str, float] = {}

        # 하위 호환 단일 캐시
        self._last_heartbeat: Optional[Dict[str, Any]] = None
        self._last_battery: Optional[Dict[str, Any]] = None

        if self._connection is None and self._connection_string:
            self._init_connection(self._connection_string)

    @property
    def connection(self) -> Any:
        """현재 MAVLink 통신 연결 객체를 반환합니다."""
        return self._connection

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
            self._send_gcs_heartbeat_and_stream_request()
            try:
                from src.features.dashboard.shell.flight_command_service import get_flight_command_service
                get_flight_command_service().set_connection(self._connection)
            except Exception:
                pass
        except Exception as exc:
            logger.error("MAVLink 연결 실패: %s - 사유: %s", conn_str, str(exc))
            self._connection = None
            self._is_connected = False

    def _send_gcs_heartbeat_and_stream_request(self) -> None:
        """FCU로 GCS 하트비트 및 전체 텔레메트리 스트림 전송을 능동적으로 요청합니다.

        ArduPilot/PX4는 GCS의 하트비트 및 데이터 스트림 요청이 없으면
        대역폭 절약을 위해 텔레메트리 스트림을 개방하지 않으므로 자립적 송출이 필수적입니다.
        """
        if not self.is_connected or not self._connection:
            return

        mav = getattr(self._connection, "mav", None)
        if not mav:
            return

        now = time.time()
        if (now - self._last_heartbeat_sent) < self._heartbeat_interval:
            return

        self._last_heartbeat_sent = now

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
                target_sys = getattr(self._connection, "target_system", 1) or 1
                target_comp = getattr(self._connection, "target_component", 1) or 1
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

    def _handle_disconnect(self) -> None:
        """통신 단절 시 좀비 소켓을 닫고 상태를 재설정합니다."""
        self._is_connected = False
        self._last_reconnect_attempt = time.time()
        if self._connection and hasattr(self._connection, "close"):
            try:
                self._connection.close()
            except Exception:
                pass
            self._connection = None
            try:
                from src.features.dashboard.shell.flight_command_service import get_flight_command_service
                get_flight_command_service().set_connection(None)
            except Exception:
                pass
            logger.warning("MAVLink 통신 단절 감지 - 재연결 대기 (기체: %s)", self._drone_id)

    def _try_auto_reconnect(self) -> bool:
        """미연결 상태 시 재연결 쿨다운 검사 및 조용한 자동 재연결 시도 (Early Return Flat Guard)."""
        if self.is_connected:
            return True
        now = time.time()
        if self._connection_string and (now - self._last_reconnect_attempt >= self._reconnect_interval):
            self._last_reconnect_attempt = now
            self._init_connection(self._connection_string)
        return self.is_connected

    def _handle_heartbeat(self, msg_dict: dict, target_drone_id: str) -> int:
        """HEARTBEAT 메시지 처리 및 Keep-Alive 텔레메트리 갱신."""
        self._last_heartbeat = msg_dict
        self._drone_heartbeats[target_drone_id] = msg_dict
        last_gps = self._drone_last_gps.get(target_drone_id)
        now_ts = time.time()
        if not (last_gps and (now_ts - self._drone_last_ingest_time.get(target_drone_id, 0.0) >= 1.0)):
            return 0
        bat = self._drone_batteries.get(target_drone_id, self._last_battery)
        now_iso = datetime.now(timezone.utc).isoformat()
        payload = convert_mavlink_to_payload(
            drone_id=target_drone_id,
            gps_msg=last_gps,
            heartbeat_msg=msg_dict,
            battery_msg=bat,
            timestamp=now_iso,
        )
        if payload and self._service.process_telemetry(payload).success:
            self._drone_last_ingest_time[target_drone_id] = now_ts
            return 1
        return 0

    def _handle_battery(self, msg_dict: dict, target_drone_id: str) -> int:
        """BATTERY_STATUS 및 SYS_STATUS 메시지 캐싱."""
        self._last_battery = msg_dict
        self._drone_batteries[target_drone_id] = msg_dict
        return 0

    def _handle_global_position(self, msg_dict: dict, target_drone_id: str) -> int:
        """GLOBAL_POSITION_INT 메시지 수신 시 텔레메트리 적재."""
        self._drone_last_gps[target_drone_id] = msg_dict
        hb = self._drone_heartbeats.get(target_drone_id, self._last_heartbeat)
        if not hb:
            return 0
        bat = self._drone_batteries.get(target_drone_id, self._last_battery)
        now_iso = datetime.now(timezone.utc).isoformat()
        payload = convert_mavlink_to_payload(
            drone_id=target_drone_id,
            gps_msg=msg_dict,
            heartbeat_msg=hb,
            battery_msg=bat,
            timestamp=now_iso,
        )
        if payload and self._service.process_telemetry(payload).success:
            self._drone_last_ingest_time[target_drone_id] = time.time()
            logger.debug("MAVLink 텔레메트리 적재 성공: %s", target_drone_id)
            return 1
        return 0

    def _handle_statustext(self, msg_dict: dict, target_drone_id: str) -> int:
        """STATUSTEXT FCU 상태 알림 로깅."""
        raw_text = msg_dict.get("text", "")
        if isinstance(raw_text, bytes):
            raw_text = raw_text.decode("utf-8", errors="ignore")
        logger.warning("MAVLink FCU 상태 알림 [%s]: %s", target_drone_id, str(raw_text).strip())
        return 0

    def _handle_command_ack(self, msg_dict: dict, target_drone_id: str) -> int:
        """COMMAND_ACK 명령 응답 로깅."""
        cmd_id, res_id = msg_dict.get("command", 0), msg_dict.get("result", 0)
        logger.info("MAVLink 명령 응답 [%s]: command=%s, result=%s", target_drone_id, cmd_id, res_id)
        return 0

    _MESSAGE_DISPATCH_TABLE = {
        "HEARTBEAT": _handle_heartbeat,
        "BATTERY_STATUS": _handle_battery,
        "SYS_STATUS": _handle_battery,
        "GLOBAL_POSITION_INT": _handle_global_position,
        "STATUSTEXT": _handle_statustext,
        "COMMAND_ACK": _handle_command_ack,
    }

    def poll_once(self) -> int:
        """논블로킹 방식으로 가용한 MAVLink 메시지를 1회 순회 소비합니다.

        Returns:
            int: 처리된 텔레메트리 적재 횟수.
        """
        # 1. 미연결 상태 시 재연결 쿨다운 검사 및 조용한 자동 재연결 시도
        if not self._try_auto_reconnect():
            return 0

        # 2. FCU 텔레메트리 침묵 방어: 1초 주기 GCS 하트비트 및 데이터 스트림 능동 요청
        self._send_gcs_heartbeat_and_stream_request()

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

                handler = self._MESSAGE_DISPATCH_TABLE.get(msg_type)
                if handler:
                    processed_count += handler(self, msg_dict, target_drone_id)
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
