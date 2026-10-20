# -*- coding: utf-8 -*-
# [파일명]: geofence_core.py
# [목적]: 지오펜스(Geo-Fence) 및 비행 금지 구역(NFZ) 순수 기하 연산 코어 (외부 I/O 0건)
from dataclasses import dataclass
import math
from typing import Any, List, Optional, Sequence, Tuple


@dataclass(frozen=True)
class GeofenceResult:
    """지오펜스 판정 결과 불변 데이터 객체."""
    drone_id: str
    is_breached: bool
    breach_type: Optional[str]
    reason: str
    recommended_status: str


def is_valid_wgs84(latitude: float, longitude: float) -> bool:
    """WGS84 좌표계 물리적 실존 범위 검증 (Pure Function)."""
    try:
        lat = float(latitude)
        lon = float(longitude)
        if math.isnan(lat) or math.isnan(lon) or math.isinf(lat) or math.isinf(lon):
            return False
        return -90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0
    except (ValueError, TypeError):
        return False


def _is_ray_intersecting_edge(
    lat: float, lon: float, p1_lat: float, p1_lon: float, p2_lat: float, p2_lon: float
) -> bool:
    """단일 다각형 변과 수평 레이의 교차 여부를 판정합니다 (Early Return Flat Guard)."""
    if not (min(p1_lat, p2_lat) < lat <= max(p1_lat, p2_lat)):
        return False
    if lon > max(p1_lon, p2_lon):
        return False
    if p1_lat == p2_lat:
        return True
    xinters = (lat - p1_lat) * (p2_lon - p1_lon) / (p2_lat - p1_lat) + p1_lon
    return p1_lon == p2_lon or lon <= xinters


def is_point_in_polygon(
    lat: float,
    lon: float,
    polygon: Sequence[Any]
) -> bool:
    """점-다각형 Ray-Casting 순수 기하 알고리즘.
    
    점(lat, lon)에서 발사한 반직선과 다각형 변의 교차 횟수가 홀수면 내부(True), 짝수면 외부(False).
    """
    n = len(polygon)
    if n < 3:
        return False

    inside = False
    p1 = polygon[0]
    p1_lat, p1_lon = float(p1[0]), float(p1[1])

    for i in range(1, n + 1):
        p2 = polygon[i % n]
        p2_lat, p2_lon = float(p2[0]), float(p2[1])

        if _is_ray_intersecting_edge(lat, lon, p1_lat, p1_lon, p2_lat, p2_lon):
            inside = not inside

        p1_lat, p1_lon = p2_lat, p2_lon

    return inside


def is_point_in_circle(
    lat: float,
    lon: float,
    center_lat: float,
    center_lon: float,
    radius_meters: float
) -> bool:
    """Haversine 대원 거리 공식을 사용한 원형 구역 포함 여부 판정 (Pure Function)."""
    earth_radius = 6371000.0  # 지구 평균 반지름 (미터)

    phi1 = math.radians(center_lat)
    phi2 = math.radians(lat)
    delta_phi = math.radians(lat - center_lat)
    delta_lambda = math.radians(lon - center_lon)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    # 부동소수점 오차로 1.0 초과 방지 클램핑
    a = min(1.0, max(0.0, a))
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    distance = earth_radius * c

    return distance <= radius_meters


def evaluate_geofence(
    drone_id: str,
    latitude: float,
    longitude: float,
    allowed_polygon: Optional[Sequence[Any]] = None,
    nfz_list: Optional[Sequence[dict[str, Any]]] = None,
) -> GeofenceResult:
    """CONSTITUTION 4대 공리 3항(지오펜스 이탈 즉시 EMERGENCY_RTH) 종합 판정 순수 함수."""
    # 1. 좌표 물리 유효성 검문 (Fail-Safe)
    if not is_valid_wgs84(latitude, longitude):
        return GeofenceResult(
            drone_id=drone_id,
            is_breached=True,
            breach_type="INVALID_COORDINATES",
            reason=f"비정상 GPS 좌표 인입 감지: lat={latitude}, lon={longitude}",
            recommended_status="EMERGENCY_RTH",
        )

    # 2. 인가 다각형 구역 이탈 판정 (단일 가드절)
    if allowed_polygon and len(allowed_polygon) >= 3 and not is_point_in_polygon(latitude, longitude, allowed_polygon):
        return GeofenceResult(
            drone_id=drone_id,
            is_breached=True,
            breach_type="OUT_OF_BOUNDS",
            reason="인가된 비행 허용 구역(Allowed Polygon)을 이탈했습니다.",
            recommended_status="EMERGENCY_RTH",
        )

    # 3. 비행 금지 구역(NFZ) 침범 판정
    for nfz in (nfz_list or ()):
        c_lat = float(nfz.get("latitude", 0.0))
        c_lon = float(nfz.get("longitude", 0.0))
        radius = float(nfz.get("radius_meters", 0.0))
        name = str(nfz.get("name", "미지정 NFZ"))

        if is_point_in_circle(latitude, longitude, c_lat, c_lon, radius):
            return GeofenceResult(
                drone_id=drone_id,
                is_breached=True,
                breach_type="NFZ_INTRUSION",
                reason=f"비행 금지 구역 침범 감지: [{name}] 반경 {radius}m 이내 진입",
                recommended_status="EMERGENCY_RTH",
            )

    # 4. 모든 검문 통과 (안전 비행)
    return GeofenceResult(
        drone_id=drone_id,
        is_breached=False,
        breach_type=None,
        reason="지오펜스 인가 구역 정상 비행 중",
        recommended_status="IN_FLIGHT",
    )
