"""
[Shell] 엑셀/CSV 업로드 및 다운로드 FastAPI 라우트
"""
from fastapi import APIRouter, UploadFile, File
from fastapi.responses import HTMLResponse, Response
from docs.boilerplates.feature_blocks.excel_io.core import parse_csv_lines, generate_csv_text

router = APIRouter(prefix="/sample-excel", tags=["sample-excel"])


@router.post("/upload", response_class=HTMLResponse)
async def upload_csv_file(file: UploadFile = File(...)):
    """CSV 업로드 처리 및 결과 요약 HTML 반환"""
    content = await file.read()
    text = content.decode("utf-8", errors="ignore")
    valid, errors = parse_csv_lines(text)

    return HTMLResponse(content=f"""
    <div id="upload-result" class="p-4 bg-slate-800 border border-slate-700 rounded-lg space-y-2">
        <div class="text-sm font-bold text-slate-100">업로드 분석 결과</div>
        <div class="text-xs text-emerald-400">성공: {len(valid)}건 정상 수집</div>
        {f'<div class="text-xs text-rose-400">실패: {len(errors)}건 에러 제외</div>' if errors else ''}
    </div>
    """.strip())


@router.get("/download")
async def download_csv_sample():
    """샘플 CSV 다운로드 스트림 반환"""
    data = [
        {"name": "김철수", "amount": 150000},
        {"name": "이영희", "amount": 280000},
    ]
    csv_text = generate_csv_text(data, ["name", "amount"])
    return Response(
        content=csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=export_sample.csv"},
    )
