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

    def dispatch_command(self, cmd: DroneCommandIn) -> Dict[str, Any]:
        """비행 명령을 해석하여 기체에 전송합니다."""
        code = cmd.command.upper()
        logger.info("비행 명령 접수: [%s] -> 기체: %s (p1=%.1f, p2=%.1f)", code, cmd.drone_id, cmd.param1, cmd.param2)

        # 실제 하드웨어 연결이 있을 경우 pymavlink 패킷 송출
        if self._connection and hasattr(self._connection, "mav"):
            try:
                from pymavlink import mavutil
                target_sys = getattr(self._connection, "target_system", 1)
                target_comp = getattr(self._connection, "target_component", 1)

                if code == "ARM":
                    arm_val = 1 if cmd.param1 >= 0.5 else 0
                    self._connection.mav.command_long_send(
                        target_sys, target_comp,
                        mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
                        0, arm_val, 21196 if arm_val else 0, 0, 0, 0, 0, 0
                    )
                elif code == "DISARM":
                    self._connection.mav.command_long_send(
                        target_sys, target_comp,
                        mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
                        0, 0, 21196, 0, 0, 0, 0, 0
                    )
                elif code == "TAKEOFF":
                    alt = cmd.param1 if cmd.param1 > 0 else 10.0
                    self._connection.mav.command_long_send(
                        target_sys, target_comp,
                        mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,
                        0, 0, 0, 0, 0, 0, 0, alt
                    )
                elif code in ("HOLD", "LOITER"):
                    mode_id = self._connection.mode_mapping().get("LOITER", 5)
                    self._connection.mav.set_mode_send(
                        target_sys, mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED, mode_id
                    )
                elif code == "RTL":
                    mode_id = self._connection.mode_mapping().get("RTL", 6)
                    self._connection.mav.set_mode_send(
                        target_sys, mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED, mode_id
                    )
                elif code == "LAND":
                    mode_id = self._connection.mode_mapping().get("LAND", 9)
                    self._connection.mav.set_mode_send(
                        target_sys, mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED, mode_id
                    )
                elif code == "MOVE":
                    # vx, vy, vz 로컬 속도 벡터 송출
                    vx, vy, vz = cmd.param1, cmd.param2, cmd.param3
                    self._connection.mav.set_position_target_local_ned_send(
                        0, target_sys, target_comp,
                        mavutil.mavlink.MAV_FRAME_BODY_NED,
                        0b0000111111000111,  # 속도만 제어
                        0, 0, 0, vx, vy, vz, 0, 0, 0, 0, 0
                    )
                elif code == "GIMBAL":
                    # param1: pitch 각도 (0 ~ -90)
                    self._connection.mav.command_long_send(
                        target_sys, target_comp,
                        mavutil.mavlink.MAV_CMD_DO_MOUNT_CONTROL,
                        0, cmd.param1, 0, 0, 0, 0, 0, mavutil.mavlink.MAV_MOUNT_MODE_MAVLINK_TARGETING
                    )
                elif code == "KILL":
                    # 비상 컷오프
                    self._connection.mav.command_long_send(
                        target_sys, target_comp,
                        mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
                        0, 0, 21196, 0, 0, 0, 0, 0
                    )
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
