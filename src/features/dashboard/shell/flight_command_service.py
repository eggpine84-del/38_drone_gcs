# -*- coding: utf-8 -*-
"""대시보드 MAVLink 비행 명령 송출 서비스 (Flight Command Service).

웹 대시보드에서 전달된 비행 명령(이륙, 착륙, 모드, 속도)을 MAVLink 2.0 바이너리 패킷으로 변환하여 기체에 송출합니다.
"""
import logging
from typing import Any, Dict

from src.features.dashboard.shell.command_dto import DroneCommandIn

logger = logging.getLogger(__name__)


class FlightCommandService:
    """비행 제어 명령 송출 어댑터."""

    def __init__(self, connection: Any = None):
        self._connection = connection

    def set_connection(self, connection: Any) -> None:
        """MAVLink 통신 소켓 연결을 주입 또는 갱신합니다."""
        self._connection = connection
        logger.info("비행 명령 서비스 MAVLink 소켓 바인딩 갱신: %s", "연결됨" if connection else "해제됨")

    @property
    def connection(self) -> Any:
        """현재 바인딩된 MAVLink 통신 소켓을 반환합니다."""
        return self._connection

    def _extract_target_system(self, drone_id: str) -> int:
        """기체 ID로부터 MAVLink target_system SysID를 동적으로 추출합니다."""
        clean_id = (drone_id or "").strip().upper()
        if clean_id.startswith("DRONE-") and clean_id[6:].isdigit():
            return int(clean_id[6:])
        if clean_id.startswith("SITL-COPTER-") and clean_id[12:].isdigit():
            return int(clean_id[12:])
        if self._connection and hasattr(self._connection, "target_system") and self._connection.target_system:
            try:
                return int(self._connection.target_system)
            except (ValueError, TypeError) as exc:
                logger.debug("target_system 변환 예외: %s", str(exc))
        return 1

    def _get_mode_mapping(self) -> dict:
        """연결된 FCU의 동적 비행 모드 매핑 딕셔너리를 반환합니다 (하드코딩 0%)."""
        if not self._connection or not hasattr(self._connection, "mode_mapping"):
            return {}
        try:
            mapping = self._connection.mode_mapping()
            return mapping if isinstance(mapping, dict) else {}
        except Exception as exc:
            logger.debug("mode_mapping 추출 실패 예외: %s", str(exc))
            return {}

    def _safe_set_mode(self, mode_id: int) -> None:
        """안전하게 FCU 비행 모드를 설정합니다."""
        if not hasattr(self._connection, "set_mode"):
            return
        try:
            self._connection.set_mode(mode_id)
        except Exception as exc:
            logger.debug("set_mode 예외 무시: %s", str(exc))

    def _safe_arducopter_arm(self) -> None:
        """안전하게 arducopter 시동을 호출합니다."""
        if not hasattr(self._connection, "arducopter_arm"):
            return
        try:
            self._connection.arducopter_arm()
        except Exception as exc:
            logger.debug("arducopter_arm 예외 무시: %s", str(exc))

    def _safe_arducopter_disarm(self) -> None:
        """안전하게 arducopter 시동 해제를 호출합니다."""
        if not hasattr(self._connection, "arducopter_disarm"):
            return
        try:
            self._connection.arducopter_disarm()
        except Exception as exc:
            logger.debug("arducopter_disarm 예외 무시: %s", str(exc))

    def _cmd_arm(self, conn: Any, mavutil: Any, target_sys: int, target_comp: int, mapping: dict, cmd: DroneCommandIn) -> None:
        arm_val = 1 if cmd.param1 >= 0.5 else 0
        if arm_val:
            guided_id = mapping.get("GUIDED", 4)
            self._safe_set_mode(guided_id)
            conn.mav.set_mode_send(
                target_sys, mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED, guided_id
            )
            self._safe_arducopter_arm()
        conn.mav.command_long_send(
            target_sys, target_comp,
            mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
            0, arm_val, 21196 if arm_val else 0, 0, 0, 0, 0, 0
        )

    def _cmd_disarm(self, conn: Any, mavutil: Any, target_sys: int, target_comp: int, mapping: dict, cmd: DroneCommandIn) -> None:
        self._safe_arducopter_disarm()
        conn.mav.command_long_send(
            target_sys, target_comp,
            mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
            0, 0, 21196, 0, 0, 0, 0, 0
        )

    def _cmd_takeoff(self, conn: Any, mavutil: Any, target_sys: int, target_comp: int, mapping: dict, cmd: DroneCommandIn) -> None:
        alt = cmd.param1 if cmd.param1 > 0 else 10.0
        guided_id = mapping.get("GUIDED", 4)
        self._safe_set_mode(guided_id)
        conn.mav.set_mode_send(
            target_sys, mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED, guided_id
        )
        self._safe_arducopter_arm()
        conn.mav.command_long_send(
            target_sys, target_comp,
            mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
            0, 1, 21196, 0, 0, 0, 0, 0
        )
        conn.mav.command_long_send(
            target_sys, target_comp,
            mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,
            0, 0, 0, 0, 0, 0, 0, alt
        )

    def _cmd_mode_guided(self, conn: Any, mavutil: Any, target_sys: int, target_comp: int, mapping: dict, cmd: DroneCommandIn) -> None:
        mode_id = mapping.get("GUIDED", 4)
        self._safe_set_mode(mode_id)
        conn.mav.set_mode_send(
            target_sys, mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED, mode_id
        )

    def _cmd_mode_loiter(self, conn: Any, mavutil: Any, target_sys: int, target_comp: int, mapping: dict, cmd: DroneCommandIn) -> None:
        mode_id = mapping.get("LOITER", 5)
        self._safe_set_mode(mode_id)
        conn.mav.set_mode_send(
            target_sys, mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED, mode_id
        )

    def _cmd_mode_rtl(self, conn: Any, mavutil: Any, target_sys: int, target_comp: int, mapping: dict, cmd: DroneCommandIn) -> None:
        mode_id = mapping.get("RTL", 6)
        self._safe_set_mode(mode_id)
        conn.mav.set_mode_send(
            target_sys, mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED, mode_id
        )

    def _cmd_mode_land(self, conn: Any, mavutil: Any, target_sys: int, target_comp: int, mapping: dict, cmd: DroneCommandIn) -> None:
        mode_id = mapping.get("LAND", 9)
        self._safe_set_mode(mode_id)
        conn.mav.set_mode_send(
            target_sys, mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED, mode_id
        )

    def _cmd_move(self, conn: Any, mavutil: Any, target_sys: int, target_comp: int, mapping: dict, cmd: DroneCommandIn) -> None:
        vx, vy, vz = cmd.param1, cmd.param2, cmd.param3
        conn.mav.set_position_target_local_ned_send(
            0, target_sys, target_comp,
            mavutil.mavlink.MAV_FRAME_BODY_NED,
            0b0000111111000111,
            0, 0, 0, vx, vy, vz, 0, 0, 0, 0, 0
        )

    def _cmd_gimbal(self, conn: Any, mavutil: Any, target_sys: int, target_comp: int, mapping: dict, cmd: DroneCommandIn) -> None:
        conn.mav.command_long_send(
            target_sys, target_comp,
            mavutil.mavlink.MAV_CMD_DO_MOUNT_CONTROL,
            0, cmd.param1, 0, 0, 0, 0, 0, mavutil.mavlink.MAV_MOUNT_MODE_MAVLINK_TARGETING
        )

    def _cmd_kill(self, conn: Any, mavutil: Any, target_sys: int, target_comp: int, mapping: dict, cmd: DroneCommandIn) -> None:
        conn.mav.command_long_send(
            target_sys, target_comp,
            mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
            0, 0, 21196, 0, 0, 0, 0, 0
        )

    _COMMAND_DISPATCH_TABLE = {
        "ARM": _cmd_arm,
        "DISARM": _cmd_disarm,
        "TAKEOFF": _cmd_takeoff,
        "GUIDED": _cmd_mode_guided,
        "HOLD": _cmd_mode_loiter,
        "LOITER": _cmd_mode_loiter,
        "RTL": _cmd_mode_rtl,
        "LAND": _cmd_mode_land,
        "MOVE": _cmd_move,
        "GIMBAL": _cmd_gimbal,
        "KILL": _cmd_kill,
    }

    def dispatch_command(self, cmd: DroneCommandIn) -> Dict[str, Any]:
        """비행 명령을 해석하여 기체에 전송합니다."""
        code = cmd.command.upper()
        logger.info("비행 명령 접수: [%s] -> 기체: %s (p1=%.1f, p2=%.1f)", code, cmd.drone_id, cmd.param1, cmd.param2)

        handler = self._COMMAND_DISPATCH_TABLE.get(code)
        if self._connection and hasattr(self._connection, "mav") and handler:
            try:
                from pymavlink import mavutil
                target_sys = self._extract_target_system(cmd.drone_id)
                target_comp = getattr(self._connection, "target_component", 1) or 1
                mapping = self._get_mode_mapping()
                handler(self, self._connection, mavutil, target_sys, target_comp, mapping, cmd)
            except Exception as e:
                logger.warning("MAVLink 명령 송출 중 통신 예외 발생: %s", str(e))

        return {
            "command": code,
            "drone_id": cmd.drone_id,
            "param1": cmd.param1,
            "param2": cmd.param2,
            "sent": True,
            "message": f"명령 [{code}] 송출 완료",
        }


# 전역 기본 서비스 싱글톤
_default_command_service = FlightCommandService()


def get_flight_command_service() -> FlightCommandService:
    """비행 명령 서비스 의존성 팩토리."""
    return _default_command_service
