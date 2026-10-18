"""
[Shell] 첨부파일 업로드 및 격리 저장 라우트 (FastAPI + HTMX)
"""
import os
from fastapi import APIRouter, UploadFile, File
from fastapi.responses import JSONResponse
from docs.boilerplates.feature_blocks.file_storage.core import validate_and_sanitize_file

router = APIRouter(prefix="/sample-storage", tags=["sample-storage"])
UPLOAD_DIR = os.path.join("temp_storage", "uploads")


@router.post("/upload")
async def upload_file_endpoint(file: UploadFile = File(...)):
    """첨부파일 업로드 및 물리 디스크 격리 저장 Shell."""
    raw_content = await file.read()
    res = validate_and_sanitize_file(
        raw_bytes=raw_content,
        original_filename=file.filename or "unknown.dat",
    )
    if not res["success"]:
        return JSONResponse(status_code=400, content={"success": False, "error": res["error"]})

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    safe_path = os.path.join(UPLOAD_DIR, res["data"]["safe_filename"])
    with open(safe_path, "wb") as f:
        f.write(raw_content)

    return JSONResponse(
        status_code=200,
        content={
            "success": True,
            "data": {
                "safe_filename": res["data"]["safe_filename"],
                "mime_type": res["data"]["mime_type"],
                "size": res["data"]["size"],
            },
        },
    )
