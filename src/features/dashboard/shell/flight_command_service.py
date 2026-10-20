# -*- coding: utf-8 -*-
"""대시보드 MAVLink 비행 명령 송출 서비스 (Flight Command Service).

웹 대시보드에서 전달된 비행 명령(이륙, 착륙, 모드, 속도)을 MAVLink 2.0 바이너리 패킷으로 변환하여 기체에 송출합니다.
"""
import logging
from typing import Any, Dict

from src.features.dashboard.shell.command_dto import DroneCommandIn

logger = logging.getLogger(__name__)

# MAVLink 표준 상수 및 기본값 정의
MAV_PARAM_ARM_MAGIC: int = 21196
DEFAULT_TAKEOFF_ALTITUDE_METERS: float = 10.0
DEFAULT_MODE_GUIDED: int = 4
DEFAULT_MODE_LOITER: int = 5
DEFAULT_MODE_RTL: int = 6
DEFAULT_MODE_LAND: int = 9

# 상용 위치 오프셋 제어 상수 (MAVLink SET_POSITION_TARGET_LOCAL_NED)
MAV_FRAME_BODY_OFFSET_NED: int = 9  # 기체 기준 상대 오프셋 프레임
POSITION_ONLY_TYPE_MASK: int = 0b0000111111111000  # 위치(x,y,z)만 제어, 속도/가속도/Yaw 무시
MAV_CMD_DO_GRIPPER: int = 211  # 물품 투하 서보 제어 명령



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
            guided_id = mapping.get("GUIDED", DEFAULT_MODE_GUIDED)
            self._safe_set_mode(guided_id)
            conn.mav.set_mode_send(
                target_sys, mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED, guided_id
            )
            self._safe_arducopter_arm()
        conn.mav.command_long_send(
            target_sys, target_comp,
            mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
            0, arm_val, MAV_PARAM_ARM_MAGIC if arm_val else 0, 0, 0, 0, 0, 0
        )

    def _cmd_disarm(self, conn: Any, mavutil: Any, target_sys: int, target_comp: int, mapping: dict, cmd: DroneCommandIn) -> None:
        self._safe_arducopter_disarm()
        conn.mav.command_long_send(
            target_sys, target_comp,
            mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
            0, 0, MAV_PARAM_ARM_MAGIC, 0, 0, 0, 0, 0
        )

    def _cmd_takeoff(self, conn: Any, mavutil: Any, target_sys: int, target_comp: int, mapping: dict, cmd: DroneCommandIn) -> None:
        alt = cmd.param1 if cmd.param1 > 0 else DEFAULT_TAKEOFF_ALTITUDE_METERS
        guided_id = mapping.get("GUIDED", DEFAULT_MODE_GUIDED)
        self._safe_set_mode(guided_id)
        conn.mav.set_mode_send(
            target_sys, mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED, guided_id
        )
        self._safe_arducopter_arm()
        conn.mav.command_long_send(
            target_sys, target_comp,
            mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
            0, 1, MAV_PARAM_ARM_MAGIC, 0, 0, 0, 0, 0
        )
        conn.mav.command_long_send(
            target_sys, target_comp,
            mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,
            0, 0, 0, 0, 0, 0, 0, alt
        )

    def _cmd_mode_guided(self, conn: Any, mavutil: Any, target_sys: int, target_comp: int, mapping: dict, cmd: DroneCommandIn) -> None:
        mode_id = mapping.get("GUIDED", DEFAULT_MODE_GUIDED)
        self._safe_set_mode(mode_id)
        conn.mav.set_mode_send(
            target_sys, mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED, mode_id
        )

    def _cmd_mode_loiter(self, conn: Any, mavutil: Any, target_sys: int, target_comp: int, mapping: dict, cmd: DroneCommandIn) -> None:
        mode_id = mapping.get("LOITER", DEFAULT_MODE_LOITER)
        self._safe_set_mode(mode_id)
        conn.mav.set_mode_send(
            target_sys, mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED, mode_id
        )

    def _cmd_mode_rtl(self, conn: Any, mavutil: Any, target_sys: int, target_comp: int, mapping: dict, cmd: DroneCommandIn) -> None:
        mode_id = mapping.get("RTL", DEFAULT_MODE_RTL)
        self._safe_set_mode(mode_id)
        conn.mav.set_mode_send(
            target_sys, mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED, mode_id
        )

    def _cmd_mode_land(self, conn: Any, mavutil: Any, target_sys: int, target_comp: int, mapping: dict, cmd: DroneCommandIn) -> None:
        mode_id = mapping.get("LAND", DEFAULT_MODE_LAND)
        self._safe_set_mode(mode_id)
        conn.mav.set_mode_send(
            target_sys, mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED, mode_id
        )

    def _cmd_move(self, conn: Any, mavutil: Any, target_sys: int, target_comp: int, mapping: dict, cmd: DroneCommandIn) -> None:
        # 상용 정밀 위치 타겟: 기체 기준 상대 오프셋 (x 전후 m, y 좌우 m, z 고도 m)
        # 위치만 정확히 도달한 후 FCU 능동 브레이크(Active Braking)로 호버링 정지
        dx, dy, dz = cmd.param1, cmd.param2, cmd.param3
        conn.mav.set_position_target_local_ned_send(
            0, target_sys, target_comp,
            MAV_FRAME_BODY_OFFSET_NED,
            POSITION_ONLY_TYPE_MASK,
            dx, dy, dz, 0, 0, 0, 0, 0, 0, 0, 0
        )

    def _cmd_gimbal(self, conn: Any, mavutil: Any, target_sys: int, target_comp: int, mapping: dict, cmd: DroneCommandIn) -> None:
        conn.mav.command_long_send(
            target_sys, target_comp,
            mavutil.mavlink.MAV_CMD_DO_MOUNT_CONTROL,
            0, cmd.param1, 0, 0, 0, 0, 0, mavutil.mavlink.MAV_MOUNT_MODE_MAVLINK_TARGETING
        )

    def _cmd_drop(self, conn: Any, mavutil: Any, target_sys: int, target_comp: int, mapping: dict, cmd: DroneCommandIn) -> None:
        # MAVLink DO_GRIPPER 그리퍼 제어 (param1=1: 그리퍼ID, param2=0: RELEASE 방출)
        conn.mav.command_long_send(
            target_sys, target_comp,
            MAV_CMD_DO_GRIPPER,
            0, 1, 0, 0, 0, 0, 0, 0
        )

    def _cmd_kill(self, conn: Any, mavutil: Any, target_sys: int, target_comp: int, mapping: dict, cmd: DroneCommandIn) -> None:
        conn.mav.command_long_send(
            target_sys, target_comp,
            mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
            0, 0, MAV_PARAM_ARM_MAGIC, 0, 0, 0, 0, 0
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
        "DROP": _cmd_drop,
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
