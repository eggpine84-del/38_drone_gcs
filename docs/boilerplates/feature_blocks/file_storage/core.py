"""
[Core] 첨부파일 바이너리 무결성 및 파일명 살균 순수 검증 모듈 (FCIS Pure Core)
"""
import uuid
from typing import Dict, Any, TypedDict, Optional, Set

# 허용된 파일 매직 넘버(시그니처 바이트) 매핑 테이블 (Table-Driven)
MAGIC_SIGNATURES: Dict[str, bytes] = {
    "image/png": b"\x89PNG\r\n\x1a\n",
    "image/jpeg": b"\xff\xd8\xff",
    "application/pdf": b"%PDF-",
}

# 확장자별 MIME 타입 매핑 (Table-Driven)
EXT_MIME_MAP: Dict[str, str] = {
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "pdf": "application/pdf",
}


class FileValidationResult(TypedDict):
    success: bool
    data: Optional[Dict[str, Any]]
    error: Optional[str]


def validate_and_sanitize_file(
    raw_bytes: bytes,
    original_filename: str,
    max_bytes: int = 5 * 1024 * 1024,
    allowed_exts: Optional[Set[str]] = None,
) -> FileValidationResult:
    """파일 바이너리 시그니처와 파일명을 검증하고 안전한 UUID 파일명을 생성한다."""
    if allowed_exts is None:
        allowed_exts = {"png", "jpg", "jpeg", "pdf"}

    # 1. 크기 검증
    size = len(raw_bytes)
    if size == 0:
        return {"success": False, "data": None, "error": "ERR_EMPTY_FILE"}
    if size > max_bytes:
        return {"success": False, "data": None, "error": "ERR_FILE_TOO_LARGE"}

    # 2. 파일명 살균 및 확장자 추출
    cleaned_name = original_filename.replace("\\", "/").split("/")[-1].strip()
    if not cleaned_name or "." not in cleaned_name:
        return {"success": False, "data": None, "error": "ERR_INVALID_FILENAME"}

    ext = cleaned_name.rsplit(".", 1)[-1].lower()
    if ext not in allowed_exts:
        return {"success": False, "data": None, "error": "ERR_UNSUPPORTED_EXTENSION"}

    expected_mime = EXT_MIME_MAP.get(ext)
    if not expected_mime:
        return {"success": False, "data": None, "error": "ERR_UNSUPPORTED_MIME"}

    # 3. 매직 넘버(바이너리 시그니처) 대조
    expected_magic = MAGIC_SIGNATURES.get(expected_mime, b"")
    if not raw_bytes.startswith(expected_magic):
        return {"success": False, "data": None, "error": "ERR_INVALID_FILE_SIGNATURE"}

    # 4. 안전한 UUID 파일명 생성
    safe_filename = f"{uuid.uuid4().hex}.{ext}"

    return {
        "success": True,
        "data": {
            "original_filename": cleaned_name,
            "safe_filename": safe_filename,
            "mime_type": expected_mime,
            "size": size,
        },
        "error": None,
    }
