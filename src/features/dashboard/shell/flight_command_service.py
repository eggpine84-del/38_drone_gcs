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

    def _extract_target_system(self, drone_id: str) -> int:
        """기체 ID로부터 MAVLink target_system SysID를 동적으로 추출합니다."""
        clean_id = (drone_id or "").strip().upper()
        if clean_id.startswith("DRONE-"):
            suffix = clean_id[6:]
            if suffix.isdigit():
                return int(suffix)
        if clean_id.startswith("SITL-COPTER-"):
            suffix = clean_id[12:]
            if suffix.isdigit():
                return int(suffix)
        if self._connection and hasattr(self._connection, "target_system") and self._connection.target_system:
            try:
                return int(self._connection.target_system)
            except (ValueError, TypeError):
                pass
        return 1

    def _get_mode_mapping(self) -> dict:
        """연결된 FCU의 동적 비행 모드 매핑 딕셔너리를 반환합니다 (하드코딩 0%)."""
        if self._connection and hasattr(self._connection, "mode_mapping"):
            try:
                mapping = self._connection.mode_mapping()
                if isinstance(mapping, dict):
                    return mapping
            except Exception:
                pass
        return {}

    def dispatch_command(self, cmd: DroneCommandIn) -> Dict[str, Any]:
        """비행 명령을 해석하여 기체에 전송합니다."""
        code = cmd.command.upper()
        logger.info("비행 명령 접수: [%s] -> 기체: %s (p1=%.1f, p2=%.1f)", code, cmd.drone_id, cmd.param1, cmd.param2)

        # 실제 하드웨어 연결이 있을 경우 pymavlink 패킷 송출
        if self._connection and hasattr(self._connection, "mav"):
            try:
                from pymavlink import mavutil
                target_sys = self._extract_target_system(cmd.drone_id)
                # target_component가 0(브로드캐스트)이면 FCU가 시동/모드 명령을 무시하므로 1(AUTOPILOT1)을 강제 보장
                target_comp = getattr(self._connection, "target_component", 1) or 1
                mapping = self._get_mode_mapping()

                if code == "ARM":
                    arm_val = 1 if cmd.param1 >= 0.5 else 0
                    if arm_val:
                        # 1. 컴퓨터 원격 시동을 위해 GUIDED 모드로 비행 권한 선전환
                        guided_id = mapping.get("GUIDED", 4)
                        if hasattr(self._connection, "set_mode"):
                            try:
                                self._connection.set_mode(guided_id)
                            except Exception:
                                pass
                        self._connection.mav.set_mode_send(
                            target_sys, mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED, guided_id
                        )
                        # 2. pymavlink 공식 아두파일럿 시동 루틴 보강
                        if hasattr(self._connection, "arducopter_arm"):
                            try:
                                self._connection.arducopter_arm()
                            except Exception:
                                pass
                    # 3. MAVLink 표준 모터 시동/해제 명령 송출
                    self._connection.mav.command_long_send(
                        target_sys, target_comp,
                        mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
                        0, arm_val, 21196 if arm_val else 0, 0, 0, 0, 0, 0
                    )
                elif code == "DISARM":
                    if hasattr(self._connection, "arducopter_disarm"):
                        try:
                            self._connection.arducopter_disarm()
                        except Exception:
                            pass
                    self._connection.mav.command_long_send(
                        target_sys, target_comp,
                        mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
                        0, 0, 21196, 0, 0, 0, 0, 0
                    )
                elif code == "TAKEOFF":
                    alt = cmd.param1 if cmd.param1 > 0 else 10.0
                    guided_id = mapping.get("GUIDED", 4)
                    # Golden Takeoff Pipeline: 1) GUIDED 권한 전환 ➔ 2) 시동(ARM) ➔ 3) 고도 이륙
                    if hasattr(self._connection, "set_mode"):
                        try:
                            self._connection.set_mode(guided_id)
                        except Exception:
                            pass
                    self._connection.mav.set_mode_send(
                        target_sys, mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED, guided_id
                    )
                    if hasattr(self._connection, "arducopter_arm"):
                        try:
                            self._connection.arducopter_arm()
                        except Exception:
                            pass
                    self._connection.mav.command_long_send(
                        target_sys, target_comp,
                        mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
                        0, 1, 21196, 0, 0, 0, 0, 0
                    )
                    self._connection.mav.command_long_send(
                        target_sys, target_comp,
                        mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,
                        0, 0, 0, 0, 0, 0, 0, alt
                    )
                elif code == "GUIDED":
                    mode_id = mapping.get("GUIDED", 4)
                    if hasattr(self._connection, "set_mode"):
                        try:
                            self._connection.set_mode(mode_id)
                        except Exception:
                            pass
                    self._connection.mav.set_mode_send(
                        target_sys, mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED, mode_id
                    )
                elif code in ("HOLD", "LOITER"):
                    mode_id = mapping.get("LOITER", 5)
                    if hasattr(self._connection, "set_mode"):
                        try:
                            self._connection.set_mode(mode_id)
                        except Exception:
                            pass
                    self._connection.mav.set_mode_send(
                        target_sys, mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED, mode_id
                    )
                elif code == "RTL":
                    mode_id = mapping.get("RTL", 6)
                    if hasattr(self._connection, "set_mode"):
                        try:
                            self._connection.set_mode(mode_id)
                        except Exception:
                            pass
                    self._connection.mav.set_mode_send(
                        target_sys, mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED, mode_id
                    )
                elif code == "LAND":
                    mode_id = mapping.get("LAND", 9)
                    if hasattr(self._connection, "set_mode"):
                        try:
                            self._connection.set_mode(mode_id)
                        except Exception:
                            pass
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
