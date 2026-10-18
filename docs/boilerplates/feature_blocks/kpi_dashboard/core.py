"""
[Core] KPI 대시보드 순수 계산 연산 함수 (Pure Core)
"""
from typing import List, Dict, Any, TypedDict


class MetricItem(TypedDict):
    value: int
    change_rate: float
    trend: str  # UP, DOWN, SAME


def calculate_kpi_metrics(current_records: List[Dict[str, Any]], previous_records: List[Dict[str, Any]]) -> Dict[str, MetricItem]:
    """매출 총합 및 이전 기간 대비 증감율을 순수 연산한다 (0 나누기 방어)."""
    curr_sales = sum(int(r.get("amount", 0)) for r in (current_records or []))
    prev_sales = sum(int(r.get("amount", 0)) for r in (previous_records or []))

    if prev_sales == 0:
        change_rate = 0.0
    else:
        change_rate = round(((curr_sales - prev_sales) / prev_sales) * 100.0, 1)

    trend = "UP" if change_rate > 0 else ("DOWN" if change_rate < 0 else "SAME")

    return {
        "total_sales": {
            "value": curr_sales,
            "change_rate": change_rate,
            "trend": trend,
        },
        "active_users": {
            "value": len(current_records or []),
            "change_rate": 0.0,
            "trend": "SAME",
        },
    }
