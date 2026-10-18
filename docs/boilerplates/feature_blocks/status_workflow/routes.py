"""
[Shell] 상태 전이 워크플로우 FastAPI 라우트
"""
from fastapi import APIRouter, Form
from fastapi.responses import HTMLResponse
from docs.boilerplates.feature_blocks.status_workflow.core import transition_order_status

router = APIRouter(prefix="/sample-workflow", tags=["sample-workflow"])


@router.post("/{order_id}/transition", response_class=HTMLResponse)
async def change_status(order_id: str, current_status: str = Form(...), target_status: str = Form(...)):
    """상태 변경 실행 후 배지 HTML 조각 반환"""
    # 실제로는 세션에서 role 획득
    res = transition_order_status(current_status, target_status, role="ADMIN")
    if not res["success"]:
        return HTMLResponse(
            content=f"""<div id="toast" hx-swap-oob="true" class="text-xs text-rose-400 p-2 bg-rose-950/80 rounded border border-rose-500/30">상태 변경 불가: {res['error']}</div>""",
            status_code=400,
        )

    new_status = res["data"]["status"]
    color_map = {
        "APPROVED": "bg-indigo-500/10 text-indigo-400 border-indigo-500/20",
        "PROCESSING": "bg-amber-500/10 text-amber-400 border-amber-500/20",
        "COMPLETED": "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
        "CANCELLED": "bg-rose-500/10 text-rose-400 border-rose-500/20",
    }
    badge_style = color_map.get(new_status, "bg-slate-700 text-slate-300")

    return HTMLResponse(content=f"""
    <span id="order-status-{order_id}" class="px-2.5 py-1 text-xs rounded-full border {badge_style}">
        {new_status}
    </span>
    <div id="toast" hx-swap-oob="true" class="text-xs text-emerald-400 p-2 bg-emerald-950/80 rounded border border-emerald-500/30">
        상태가 [{new_status}](으)로 변경되었습니다.
    </div>
    """.strip())
