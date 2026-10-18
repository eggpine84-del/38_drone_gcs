"""
[Shell] KPI 대시보드 FastAPI 라우트
"""
from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from docs.boilerplates.feature_blocks.kpi_dashboard.core import calculate_kpi_metrics

router = APIRouter(prefix="/sample-kpi", tags=["sample-kpi"])


@router.get("", response_class=HTMLResponse)
async def get_kpi_cards(period: str = "today"):
    """기간별 KPI 요약 카드 HTML 조각 반환 (htmx 비동기 갱신 대상)"""
    dummy_curr = [{"amount": 5400000}] if period == "today" else [{"amount": 28000000}]
    dummy_prev = [{"amount": 4800000}] if period == "today" else [{"amount": 25000000}]

    metrics = calculate_kpi_metrics(dummy_curr, dummy_prev)
    sales = metrics["total_sales"]

    trend_color = "text-emerald-400" if sales["trend"] == "UP" else "text-rose-400"
    trend_sign = "+" if sales["change_rate"] > 0 else ""

    return HTMLResponse(content=f"""
    <div id="kpi-cards-container" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div class="p-5 bg-slate-800/80 border border-slate-700/60 rounded-xl space-y-2">
            <span class="text-xs font-semibold text-slate-400">총 매출 ({period})</span>
            <div class="text-2xl font-bold text-slate-100">{sales['value']:,}원</div>
            <div class="text-xs font-medium {trend_color}">
                전기 대비 {trend_sign}{sales['change_rate']}%
            </div>
        </div>
    </div>
    """.strip())
