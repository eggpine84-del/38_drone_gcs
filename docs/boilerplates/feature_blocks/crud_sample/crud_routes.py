"""
[Shell] CRUD 라우트 및 메모리/DB 레포지토리 어댑터
- FastAPI Router 규격
- htmx 부분 렌더링 지원 (HTML 조각 또는 JSON 반환)
- Core 순수 함수를 호출하여 I/O 격리
"""
from typing import Dict, Any, List
from fastapi import APIRouter, Form, Request, HTTPException
from fastapi.responses import HTMLResponse

from docs.boilerplates.feature_blocks.crud_sample.crud_core import (
    validate_item_input,
    apply_soft_delete,
)

router = APIRouter(prefix="/sample-items", tags=["sample-crud"])

# 인메모리 샘플 저장소 (실무에서는 DB Repository 객체로 주입)
SAMPLE_DB: Dict[str, Dict[str, Any]] = {
    "1": {"item_id": "1", "name": "기본 샘플 1", "category": "TECH", "status": "ACTIVE", "is_deleted": False},
    "2": {"item_id": "2", "name": "기본 샘플 2", "category": "DESIGN", "status": "ACTIVE", "is_deleted": False},
}


def _render_row(item: Dict[str, Any]) -> str:
    """단일 행(Row) HTML 조각 렌더링 헬퍼 (htmx swap 대상)"""
    item_id = item["item_id"]
    name = item["name"]
    category = item["category"]
    status = item["status"]

    return f"""
    <tr id="item-row-{item_id}" class="hover:bg-slate-700/30 transition-colors border-b border-slate-700/50">
        <td class="p-3 text-sm font-medium text-slate-200">{item_id}</td>
        <td class="p-3 text-sm text-slate-100">{name}</td>
        <td class="p-3 text-sm text-slate-400">{category}</td>
        <td class="p-3 text-sm">
            <span class="px-2 py-0.5 text-xs rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">{status}</span>
        </td>
        <td class="p-3 text-sm text-right space-x-2">
            <button hx-get="/sample-items/{item_id}/edit"
                    hx-target="#item-row-{item_id}"
                    hx-swap="outerHTML"
                    class="px-2 py-1 text-xs font-semibold text-slate-300 hover:text-white bg-slate-700/50 hover:bg-slate-700 rounded transition-all">
                수정
            </button>
            <button hx-delete="/sample-items/{item_id}"
                    hx-target="#item-row-{item_id}"
                    hx-swap="outerHTML"
                    hx-confirm="정말 삭제하시겠습니까?"
                    class="px-2 py-1 text-xs font-semibold text-rose-400 hover:text-rose-300 bg-rose-500/10 hover:bg-rose-500/20 rounded transition-all">
                삭제
            </button>
        </td>
    </tr>
    """.strip()


@router.get("", response_class=HTMLResponse)
async def list_items():
    """목록 조회: 삭제되지 않은 활성 항목들 반환"""
    active_items = [v for v in SAMPLE_DB.values() if not v.get("is_deleted")]
    rows_html = "".join([_render_row(item) for item in active_items])
    return HTMLResponse(content=rows_html)


@router.post("", response_class=HTMLResponse)
async def create_item(name: str = Form(""), category: str = Form("GENERAL")):
    """항목 등록: 검증 실패 시 에러 반환, 성공 시 새 행(Row) 조각 반환"""
    validation = validate_item_input(name, category)
    if not validation["success"]:
        return HTMLResponse(
            content=f"""<div id="toast" hx-swap-oob="true" class="text-xs text-rose-400 p-2 bg-rose-950/80 rounded border border-rose-500/30">오류: {validation['error']}</div>""",
            status_code=400,
        )

    new_id = str(len(SAMPLE_DB) + 1)
    new_data = dict(validation["data"])
    new_data["item_id"] = new_id
    SAMPLE_DB[new_id] = new_data

    # 새로 생성된 행과 성공 토스트를 함께 반환
    toast_html = f"""<div id="toast" hx-swap-oob="true" class="text-xs text-emerald-400 p-2 bg-emerald-950/80 rounded border border-emerald-500/30">성공적으로 등록되었습니다.</div>"""
    return HTMLResponse(content=_render_row(new_data) + toast_html)


@router.get("/{item_id}/edit", response_class=HTMLResponse)
async def get_edit_row(item_id: str):
    """인라인 편집 모드: 클릭한 행을 입력 폼으로 교체"""
    item = SAMPLE_DB.get(item_id)
    if not item or item.get("is_deleted"):
        raise HTTPException(status_code=404, detail="항목을 찾을 수 없습니다.")

    return HTMLResponse(content=f"""
    <tr id="item-row-{item_id}" class="bg-slate-700/50 border-b border-indigo-500/50">
        <td class="p-3 text-sm text-slate-400">{item_id}</td>
        <td class="p-2">
            <input type="text" name="name" value="{item['name']}" class="w-full px-2 py-1 text-sm bg-slate-900 border border-slate-600 rounded text-slate-100 focus:outline-none focus:border-indigo-500" required />
        </td>
        <td class="p-2">
            <input type="text" name="category" value="{item['category']}" class="w-full px-2 py-1 text-sm bg-slate-900 border border-slate-600 rounded text-slate-100 focus:outline-none focus:border-indigo-500" />
        </td>
        <td class="p-3 text-sm text-slate-400">{item['status']}</td>
        <td class="p-3 text-sm text-right space-x-2">
            <button hx-put="/sample-items/{item_id}"
                    hx-include="closest tr"
                    hx-target="#item-row-{item_id}"
                    hx-swap="outerHTML"
                    class="px-2 py-1 text-xs font-semibold text-emerald-400 bg-emerald-500/10 hover:bg-emerald-500/20 rounded">
                저장
            </button>
            <button hx-get="/sample-items/{item_id}/cancel"
                    hx-target="#item-row-{item_id}"
                    hx-swap="outerHTML"
                    class="px-2 py-1 text-xs font-semibold text-slate-400 hover:text-slate-300">
                취소
            </button>
        </td>
    </tr>
    """.strip())


@router.get("/{item_id}/cancel", response_class=HTMLResponse)
async def cancel_edit(item_id: str):
    """인라인 편집 취소: 원래 읽기 전용 행으로 복구"""
    item = SAMPLE_DB.get(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="항목을 찾을 수 없습니다.")
    return HTMLResponse(content=_render_row(item))


@router.put("/{item_id}", response_class=HTMLResponse)
async def update_item(item_id: str, name: str = Form(...), category: str = Form("GENERAL")):
    """항목 수정 저장"""
    item = SAMPLE_DB.get(item_id)
    if not item or item.get("is_deleted"):
        raise HTTPException(status_code=404, detail="항목을 찾을 수 없습니다.")

    validation = validate_item_input(name, category)
    if not validation["success"]:
        return HTMLResponse(
            content=f"""<div id="toast" hx-swap-oob="true" class="text-xs text-rose-400 p-2 bg-rose-950/80 rounded border border-rose-500/30">수정 실패: {validation['error']}</div>""",
            status_code=400,
        )

    item["name"] = validation["data"]["name"]
    item["category"] = validation["data"]["category"]

    toast_html = f"""<div id="toast" hx-swap-oob="true" class="text-xs text-emerald-400 p-2 bg-emerald-950/80 rounded border border-emerald-500/30">수정되었습니다.</div>"""
    return HTMLResponse(content=_render_row(item) + toast_html)


@router.delete("/{item_id}", response_class=HTMLResponse)
async def delete_item(item_id: str):
    """항목 삭제 (소프트 딜리트): 빈 응답 반환하여 해당 행을 화면에서 제거"""
    item = SAMPLE_DB.get(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="항목을 찾을 수 없습니다.")

    result = apply_soft_delete(item)
    if result["success"]:
        SAMPLE_DB[item_id] = result["data"]
    toast_html = f"""<div id="toast" hx-swap-oob="true" class="text-xs text-slate-400 p-2 bg-slate-800 rounded border border-slate-700">항목이 삭제되었습니다.</div>"""
    return HTMLResponse(content=toast_html)
