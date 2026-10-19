# -*- coding: utf-8 -*-
"""MAVLink 바이너리 패킷 순수 코어 파서 (MAVLink Parser Pure Core).

FCIS 헌법 100% 준수: 외부 I/O 0건, 부작용(Side-Effect) 0건, 0.001초 결정론적 연산.
MAVLink 원시 정수 필드를 GCS 도메인 모델(IngestPayload)로 변환.
"""
import math
from typing import Any, Dict, Final, Mapping, Optional

from src.engine.core.drone_state_machine import DroneStatus
from src.engine.shell.drone_gcs_service import IngestPayload

# Table-Driven Dispatch: ArduPilot/PX4 커스텀 모드 매핑 테이블
CUSTOM_MODE_DISPATCH: Final[Mapping[int, DroneStatus]] = {
    6: DroneStatus.EMERGENCY_RTH,  # ArduPilot Copter RTL
    9: DroneStatus.LANDING,        # ArduPilot Copter LAND
}

MAV_MODE_FLAG_SAFETY_ARMED: Final[int] = 128


def map_mavlink_mode_to_status(base_mode: int, custom_mode: int, altitude: float) -> DroneStatus:
    """MAVLink 모드 플래그를 GCS 공인 비행 상태로 매핑합니다.

    Args:
        base_mode: MAVLink 기본 비행 모드 비트마스크 (시동 여부).
        custom_mode: 자동항법장치(ArduPilot) 커스텀 비행 모드 정수.
        altitude: 현재 상대 고도 (m).

    Returns:
        DroneStatus: 결정론적으로 판정된 비행 상태.
    """
    # 1. Guard Clause: 시동 해제 상태 (Disarmed)
    if not (base_mode & MAV_MODE_FLAG_SAFETY_ARMED):
        return DroneStatus.IDLE

    # 2. Table-Driven Dispatch: 특수 비행 모드 매핑
    if custom_mode in CUSTOM_MODE_DISPATCH:
        return CUSTOM_MODE_DISPATCH[custom_mode]

    # 3. 비행 고도 기반 동적 상태 판정
    if altitude > 0.5:
        return DroneStatus.IN_FLIGHT

    return DroneStatus.ARMED


def convert_mavlink_to_payload(
    drone_id: str,
    gps_msg: Dict[str, Any],
    heartbeat_msg: Dict[str, Any],
    battery_msg: Optional[Dict[str, Any]],
    timestamp: str,
) -> Optional[IngestPayload]:
    """MAVLink 메시지 세트를 GCS 단일 진실 원장 규격(IngestPayload)으로 변환합니다.

    Args:
        drone_id: 기체 식별자.
        gps_msg: GLOBAL_POSITION_INT 메시지 딕셔너리.
        heartbeat_msg: HEARTBEAT 메시지 딕셔너리.
        battery_msg: BATTERY_STATUS 또는 SYS_STATUS 메시지 딕셔너리 (옵션).
        timestamp: 주입할 ISO 타임스탬프 문자열.

    Returns:
        Optional[IngestPayload]: 유효성 검증 완료된 페이로드 (이상치 감지 시 None).
    """
    # 1. Guard Clause: 기체 식별자 검증
    if not drone_id or not drone_id.strip():
        return None

    # 2. Guard Clause: 필수 메시지 누락 차단
    if not gps_msg or not heartbeat_msg:
        return None

    # 3. Guard Clause: GPS No-Fix 및 더미(0, 0) 좌표 방어
    raw_lat = int(gps_msg.get("lat", 0))
    raw_lon = int(gps_msg.get("lon", 0))
    if raw_lat == 0 and raw_lon == 0:
        return None

    lat = raw_lat / 1e7
    lon = raw_lon / 1e7

    # 유효 좌표 범위 가드
    if not (-90.0 <= lat <= 90.0) or not (-180.0 <= lon <= 180.0):
        return None

    # 4. 상대 고도 스케일링 (mm -> m) 및 음수 클램핑
    raw_alt = int(gps_msg.get("relative_alt", 0))
    alt = max(0.0, raw_alt / 1000.0)

    # 5. 지표 속도(Ground Speed) 연산 (cm/s -> m/s)
    vx = float(gps_msg.get("vx", 0)) / 100.0
    vy = float(gps_msg.get("vy", 0)) / 100.0
    speed = max(0.0, math.sqrt(vx * vx + vy * vy))

    # 6. 배터리 잔량 백분율 클램핑 (0 ~ 100)
    raw_battery = 100
    if battery_msg:
        raw_battery = battery_msg.get("battery_remaining", 100)
    battery = max(0, min(100, int(raw_battery)))

    # 7. 비행 상태 매핑
    base_mode = int(heartbeat_msg.get("base_mode", 0))
    custom_mode = int(heartbeat_msg.get("custom_mode", 0))
    target_status = map_mavlink_mode_to_status(base_mode, custom_mode, alt)

    return IngestPayload(
        drone_id=drone_id.strip(),
        latitude=lat,
        longitude=lon,
        altitude=alt,
        speed=speed,
        battery=battery,
        target_status=target_status,
        timestamp=timestamp,
    )
