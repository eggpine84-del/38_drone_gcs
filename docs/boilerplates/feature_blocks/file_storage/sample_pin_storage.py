"""
[Pin-Test First] 6_file_storage 핀테스트 선작성
"""
import pytest
from docs.boilerplates.feature_blocks.file_storage.core import validate_and_sanitize_file


def test_file_storage_valid_png():
    """정상 PNG 파일은 유효성 통과 및 안전한 UUID 파일명이 생성되어야 한다."""
    fake_png_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
    res = validate_and_sanitize_file(
        raw_bytes=fake_png_bytes,
        original_filename="profile_photo.png",
        max_bytes=1024 * 1024,
    )
    assert res["success"] is True
    assert res["data"] is not None
    assert res["data"]["mime_type"] == "image/png"
    assert res["data"]["safe_filename"].endswith(".png")
    assert res["data"]["size"] == len(fake_png_bytes)


def test_file_storage_path_traversal_blocked():
    """상위 경로 접근(../) 시도 시 파일명이 엄격히 살균되어야 한다."""
    fake_png_bytes = b"\x89PNG\r\n\x1a\n"
    res = validate_and_sanitize_file(
        raw_bytes=fake_png_bytes,
        original_filename="../../../etc/passwd.png",
        max_bytes=1024 * 1024,
    )
    assert res["success"] is True
    assert ".." not in res["data"]["safe_filename"]
    assert "/" not in res["data"]["safe_filename"]


def test_file_storage_disguised_executable_blocked():
    """확장자만 png로 위장한 실행파일(EXE)은 바이너리 검증으로 즉각 거부되어야 한다."""
    fake_exe_bytes = b"MZ\x90\x00\x03\x00\x00\x00"
    res = validate_and_sanitize_file(
        raw_bytes=fake_exe_bytes,
        original_filename="malicious.png",
        max_bytes=1024 * 1024,
    )
    assert res["success"] is False
    assert res["error"] == "ERR_INVALID_FILE_SIGNATURE"
