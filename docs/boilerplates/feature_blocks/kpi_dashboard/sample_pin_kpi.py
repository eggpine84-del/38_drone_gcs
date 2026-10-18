"""
[Pin-Test First] 2_kpi_dashboard 핀테스트 선작성 (Red 필수)
"""
import pytest
from docs.boilerplates.kpi_dashboard.core import calculate_kpi_metrics


def test_calculate_kpi_metrics_empty():
    """빈 데이터 입력 시 DivisionByZero 없이 0값과 안전한 증감율을 반환해야 한다."""
    res = calculate_kpi_metrics([], [])
    assert res["total_sales"]["value"] == 0
    assert res["total_sales"]["change_rate"] == 0.0
    assert res["active_users"]["value"] == 0


def test_calculate_kpi_metrics_normal():
    """정상 데이터 입력 시 총합과 전주 대비 증감율이 정확히 계산되어야 한다."""
    current = [{"amount": 1000}, {"amount": 2000}]
    previous = [{"amount": 1000}, {"amount": 1000}]
    res = calculate_kpi_metrics(current, previous)
    assert res["total_sales"]["value"] == 3000
    assert res["total_sales"]["change_rate"] == 50.0  # (3000-2000)/2000 * 100
