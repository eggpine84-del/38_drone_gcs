# -*- coding: utf-8 -*-
# [파일명]: test_pin_geofence_core.py
# [목적]: 지오펜스 및 비행 금지 구역(NFZ) 순수 기하 알고리즘 선행 핀-테스트 (외부 I/O 0건)
import pytest
from src.features.geofence.core.geofence_core import (
    is_point_in_polygon,
    is_point_in_circle,
    evaluate_geofence,
    GeofenceResult,
)

# 서울 시청 중심 인가 구역 테스트 다각형 (WGS84 4각 폴리곤)
SEOUL_ALLOWED_POLYGON = [
    (37.5600, 126.9700),
    (37.5700, 126.9700),
    (37.5700, 126.9850),
    (37.5600, 126.9850),
]


def test_pin_ray_casting_polygon_interior_and_exterior():
    """점-다각형 Ray-Casting 순수 알고리즘 내부/외부 판정 검증 (Full-Assertion)."""
    # 1. 내부 좌표 (서울시청 인근)
    assert is_point_in_polygon(37.5650, 126.9750, SEOUL_ALLOWED_POLYGON) is True

    # 2. 외부 좌표 (동대문 인근 - 이탈)
    assert is_point_in_polygon(37.5710, 127.0090, SEOUL_ALLOWED_POLYGON) is False

    # 3. 비정상 다각형 (꼭짓점 2개 이하) -> Fail-Safe False 반환
    assert is_point_in_polygon(37.5650, 126.9750, [(37.5600, 126.9700), (37.5700, 126.9700)]) is False


def test_pin_circle_nfz_distance_check():
    """원형 비행 금지 구역(NFZ) 거리 판정 검증 (Full-Assertion)."""
    center_lat, center_lon = 37.5665, 126.9780
    radius_m = 500.0  # 반경 500미터

    # 1. 중심점 바로 근처 (약 50m 거리) -> 침범 (True)
    assert is_point_in_circle(37.5668, 126.9782, center_lat, center_lon, radius_m) is True

    # 2. 반경 500m 밖 (약 2km 거리) -> 안전 (False)
    assert is_point_in_circle(37.5850, 126.9780, center_lat, center_lon, radius_m) is False


def test_pin_geofence_comprehensive_evaluation():
    """지오펜스 인가 구역 및 NFZ 복합 판정 헌법 공리 3항 준수 검증."""
    nfz_list = [
        {"name": "청와대 NFZ", "latitude": 37.5866, "longitude": 126.9748, "radius_meters": 1000.0}
    ]

    # 케이스 1: 인가 구역 내부 & NFZ 밖 -> 정상 비행 허용
    normal_res: GeofenceResult = evaluate_geofence(
        drone_id="DRONE-01",
        latitude=37.5650,
        longitude=126.9750,
        allowed_polygon=SEOUL_ALLOWED_POLYGON,
        nfz_list=nfz_list,
    )
    assert normal_res.is_breached is False
    assert normal_res.breach_type is None
    assert normal_res.recommended_status == "IN_FLIGHT"

    # 케이스 2: 인가 구역 이탈 -> 즉시 EMERGENCY_RTH 강제 권한 발동
    oob_res: GeofenceResult = evaluate_geofence(
        drone_id="DRONE-01",
        latitude=37.5800,  # 폴리곤 북쪽 이탈
        longitude=126.9750,
        allowed_polygon=SEOUL_ALLOWED_POLYGON,
        nfz_list=nfz_list,
    )
    assert oob_res.is_breached is True
    assert oob_res.breach_type == "OUT_OF_BOUNDS"
    assert oob_res.recommended_status == "EMERGENCY_RTH"

    # 케이스 3: NFZ 비행 금지 구역 침범 -> 즉시 EMERGENCY_RTH 강제 권한 발동
    nfz_res: GeofenceResult = evaluate_geofence(
        drone_id="DRONE-02",
        latitude=37.5867,  # 청와대 NFZ 10m 이내 침범
        longitude=126.9749,
        allowed_polygon=[],  # 인가 구역 무제한이라도 NFZ 우선 적용
        nfz_list=nfz_list,
    )
    assert nfz_res.is_breached is True
    assert nfz_res.breach_type == "NFZ_INTRUSION"
    assert nfz_res.recommended_status == "EMERGENCY_RTH"


def test_pin_invalid_coordinates_fail_safe():
    """비정상 좌표(위경도 범위 초과) 인입 시 크래시 없이 즉시 차단(Fail-Safe) 검증."""
    invalid_res = evaluate_geofence(
        drone_id="DRONE-ERR",
        latitude=999.0,  # 유효 범위(-90~90) 초과
        longitude=126.9750,
        allowed_polygon=SEOUL_ALLOWED_POLYGON,
        nfz_list=[],
    )
    assert invalid_res.is_breached is True
    assert invalid_res.breach_type == "INVALID_COORDINATES"
    assert invalid_res.recommended_status == "EMERGENCY_RTH"


def test_pin_geofence_pure_flat_compliance():
    """지오펜스 코어가 AST 중첩 if문 없이 평탄화되었는지 검증합니다."""
    import ast
    with open("src/features/geofence/core/geofence_core.py", "r", encoding="utf-8") as f:
        tree = ast.parse(f.read())
    nested_found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "evaluate_geofence":
            for sub in ast.walk(node):
                if isinstance(sub, ast.If):
                    for child in sub.body:
                        for n in ast.walk(child):
                            if isinstance(n, ast.If):
                                nested_found.append(f"L{sub.lineno} -> L{n.lineno}")
    assert not nested_found, f"지오펜스 코어 중첩 if문 감지: {nested_found}"

