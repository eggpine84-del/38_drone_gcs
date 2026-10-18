"""
[Shell] 감사 로그 FastAPI 라우트
"""
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(prefix="/sample-audit", tags=["sample-audit"])

# 인메모리 샘플 감사 로그
AUDIT_LOGS = [
    {"user": "admin@company.com", "action": "UPDATE", "target": "사원 #102 직급", "diff": "USER -> MANAGER", "time": "2026-10-05 23:50"},
    {"user": "staff@company.com", "action": "CREATE", "target": "거래처 #99 신규 등록", "diff": "-", "time": "2026-10-05 22:15"},
]


@router.get("", response_class=HTMLResponse)
async def list_audit_logs():
    """감사 로그 타임라인 HTML 조각 반환"""
    rows_html = "".join([
        f"""
        <tr class="border-b border-slate-800 text-xs">
            <td class="p-3 text-slate-400">{log['time']}</td>
            <td class="p-3 text-slate-200 font-medium">{log['user']}</td>
            <td class="p-3"><span class="px-2 py-0.5 rounded bg-slate-800 text-slate-300">{log['action']}</span></td>
            <td class="p-3 text-slate-300">{log['target']}</td>
            <td class="p-3 text-indigo-400 font-mono">{log['diff']}</td>
        </tr>
        """.strip()
        for log in AUDIT_LOGS
    ])
    return HTMLResponse(content=rows_html)
