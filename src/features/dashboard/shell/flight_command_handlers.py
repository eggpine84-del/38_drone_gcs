"""대시보드 MAVLink 비행 명령 패킷 송출 핸들러 (Flight Command Handlers).

11종 MAVLink 명령 패킷 조립 및 디스패치 테이블 전담 서브모듈 (SRP 준수).
"""

from typing import Any

from src.features.dashboard.shell.command_dto import DroneCommandIn

# MAVLink 표준 상수 및 기본값 정의
MAV_PARAM_ARM_MAGIC: int = 21196
DEFAULT_TAKEOFF_ALTITUDE_METERS: float = 10.0
DEFAULT_MODE_GUIDED: int = 4
DEFAULT_MODE_LOITER: int = 5
DEFAULT_MODE_RTL: int = 6
DEFAULT_MODE_LAND: int = 9

# 상용 위치 오프셋 제어 상수 (MAVLink SET_POSITION_TARGET_LOCAL_NED)
MAV_FRAME_BODY_OFFSET_NED: int = 9  # 기체 기준 상대 오프셋 프레임
POSITION_ONLY_TYPE_MASK: int = (
    0b0000111111111000  # 위치(x,y,z)만 제어, 속도/가속도/Yaw 무시
)
MAV_CMD_DO_GRIPPER: int = 211  # 물품 투하 서보 제어 명령


def cmd_arm(
    service: Any,
    conn: Any,
    mavutil: Any,
    target_sys: int,
    target_comp: int,
    mapping: dict,
    cmd: DroneCommandIn,
) -> None:
    arm_val = 1 if cmd.param1 >= 0.5 else 0
    if arm_val:
        guided_id = mapping.get("GUIDED", DEFAULT_MODE_GUIDED)
        service._safe_set_mode(guided_id)
        conn.mav.set_mode_send(
            target_sys, mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED, guided_id
        )
        service._safe_arducopter_arm()
    conn.mav.command_long_send(
        target_sys,
        target_comp,
        mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
        0,
        arm_val,
        MAV_PARAM_ARM_MAGIC if arm_val else 0,
        0,
        0,
        0,
        0,
        0,
    )


def cmd_disarm(
    service: Any,
    conn: Any,
    mavutil: Any,
    target_sys: int,
    target_comp: int,
    mapping: dict,
    cmd: DroneCommandIn,
) -> None:
    service._safe_arducopter_disarm()
    conn.mav.command_long_send(
        target_sys,
        target_comp,
        mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
        0,
        0,
        MAV_PARAM_ARM_MAGIC,
        0,
        0,
        0,
        0,
        0,
    )


def cmd_takeoff(
    service: Any,
    conn: Any,
    mavutil: Any,
    target_sys: int,
    target_comp: int,
    mapping: dict,
    cmd: DroneCommandIn,
) -> None:
    alt = cmd.param1 if cmd.param1 > 0 else DEFAULT_TAKEOFF_ALTITUDE_METERS
    guided_id = mapping.get("GUIDED", DEFAULT_MODE_GUIDED)
    service._safe_set_mode(guided_id)
    conn.mav.set_mode_send(
        target_sys, mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED, guided_id
    )
    service._safe_arducopter_arm()
    conn.mav.command_long_send(
        target_sys,
        target_comp,
        mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
        0,
        1,
        MAV_PARAM_ARM_MAGIC,
        0,
        0,
        0,
        0,
        0,
    )
    conn.mav.command_long_send(
        target_sys,
        target_comp,
        mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        alt,
    )


def cmd_mode_guided(
    service: Any,
    conn: Any,
    mavutil: Any,
    target_sys: int,
    target_comp: int,
    mapping: dict,
    cmd: DroneCommandIn,
) -> None:
    mode_id = mapping.get("GUIDED", DEFAULT_MODE_GUIDED)
    service._safe_set_mode(mode_id)
    conn.mav.set_mode_send(
        target_sys, mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED, mode_id
    )


def cmd_mode_loiter(
    service: Any,
    conn: Any,
    mavutil: Any,
    target_sys: int,
    target_comp: int,
    mapping: dict,
    cmd: DroneCommandIn,
) -> None:
    mode_id = mapping.get("LOITER", DEFAULT_MODE_LOITER)
    service._safe_set_mode(mode_id)
    conn.mav.set_mode_send(
        target_sys, mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED, mode_id
    )


def cmd_mode_rtl(
    service: Any,
    conn: Any,
    mavutil: Any,
    target_sys: int,
    target_comp: int,
    mapping: dict,
    cmd: DroneCommandIn,
) -> None:
    mode_id = mapping.get("RTL", DEFAULT_MODE_RTL)
    service._safe_set_mode(mode_id)
    conn.mav.set_mode_send(
        target_sys, mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED, mode_id
    )


def cmd_mode_land(
    service: Any,
    conn: Any,
    mavutil: Any,
    target_sys: int,
    target_comp: int,
    mapping: dict,
    cmd: DroneCommandIn,
) -> None:
    mode_id = mapping.get("LAND", DEFAULT_MODE_LAND)
    service._safe_set_mode(mode_id)
    conn.mav.set_mode_send(
        target_sys, mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED, mode_id
    )


def cmd_move(
    service: Any,
    conn: Any,
    mavutil: Any,
    target_sys: int,
    target_comp: int,
    mapping: dict,
    cmd: DroneCommandIn,
) -> None:
    dx, dy, dz = cmd.param1, cmd.param2, cmd.param3
    conn.mav.set_position_target_local_ned_send(
        0,
        target_sys,
        target_comp,
        MAV_FRAME_BODY_OFFSET_NED,
        POSITION_ONLY_TYPE_MASK,
        dx,
        dy,
        dz,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
    )


def cmd_gimbal(
    service: Any,
    conn: Any,
    mavutil: Any,
    target_sys: int,
    target_comp: int,
    mapping: dict,
    cmd: DroneCommandIn,
) -> None:
    conn.mav.command_long_send(
        target_sys,
        target_comp,
        mavutil.mavlink.MAV_CMD_DO_MOUNT_CONTROL,
        0,
        cmd.param1,
        0,
        0,
        0,
        0,
        0,
        mavutil.mavlink.MAV_MOUNT_MODE_MAVLINK_TARGETING,
    )


def cmd_drop(
    service: Any,
    conn: Any,
    mavutil: Any,
    target_sys: int,
    target_comp: int,
    mapping: dict,
    cmd: DroneCommandIn,
) -> None:
    conn.mav.command_long_send(
        target_sys, target_comp, MAV_CMD_DO_GRIPPER, 0, 1, 0, 0, 0, 0, 0, 0
    )


def cmd_kill(
    service: Any,
    conn: Any,
    mavutil: Any,
    target_sys: int,
    target_comp: int,
    mapping: dict,
    cmd: DroneCommandIn,
) -> None:
    conn.mav.command_long_send(
        target_sys,
        target_comp,
        mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
        0,
        0,
        MAV_PARAM_ARM_MAGIC,
        0,
        0,
        0,
        0,
        0,
    )


COMMAND_DISPATCH_TABLE = {
    "ARM": cmd_arm,
    "DISARM": cmd_disarm,
    "TAKEOFF": cmd_takeoff,
    "GUIDED": cmd_mode_guided,
    "HOLD": cmd_mode_loiter,
    "LOITER": cmd_mode_loiter,
    "RTL": cmd_mode_rtl,
    "LAND": cmd_mode_land,
    "MOVE": cmd_move,
    "GIMBAL": cmd_gimbal,
    "DROP": cmd_drop,
    "KILL": cmd_kill,
}
