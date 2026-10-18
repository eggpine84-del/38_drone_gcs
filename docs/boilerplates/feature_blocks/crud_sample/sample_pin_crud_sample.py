"""
[Pin-Test First] CRUD 코어 및 라우트 선행 검증 테스트 (Red -> Green 보장)
"""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from docs.boilerplates.crud_sample.crud_core import (
    validate_item_input,
    apply_soft_delete,
)
from docs.boilerplates.crud_sample.crud_routes import router, SAMPLE_DB


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_core_validate_item_input_empty_name():
    """빈 이름 입력 시 즉시 실패 봉투를 반환해야 한다."""
    res = validate_item_input("", "TECH")
    assert res == {"success": False, "data": None, "error": "ERR_EMPTY_NAME"}

    res_spaces = validate_item_input("   ", "TECH")
    assert res_spaces == {"success": False, "data": None, "error": "ERR_EMPTY_NAME"}


def test_core_validate_item_input_too_short():
    """1글자 이름 입력 시 길이 부족 에러를 반환해야 한다."""
    res = validate_item_input("A", "TECH")
    assert res == {"success": False, "data": None, "error": "ERR_NAME_TOO_SHORT"}


def test_core_validate_item_input_success():
    """정상 입력 시 공백이 제거되고 ACTIVE 상태로 생성 데이터가 반환되어야 한다."""
    res = validate_item_input("  신규 상품  ", "")
    assert res == {
        "success": True,
        "data": {
            "name": "신규 상품",
            "category": "GENERAL",
            "status": "ACTIVE",
            "is_deleted": False,
        },
        "error": None,
    }


def test_core_apply_soft_delete():
    """소프트 딜리트 시 is_deleted 플래그가 True로 변경되어야 한다."""
    dummy = {"item_id": "1", "name": "기존항목", "status": "ACTIVE", "is_deleted": False}
    res = apply_soft_delete(dummy)
    assert res["success"] is True
    assert res["data"]["is_deleted"] is True
    assert res["data"]["status"] == "ARCHIVED"


def test_route_list_items(client):
    """GET /sample-items 호출 시 활성 항목들의 tr 태그 목록이 반환되어야 한다."""
    response = client.get("/sample-items")
    assert response.status_code == 200
    assert "item-row-1" in response.text
    assert "기본 샘플 1" in response.text


def test_route_create_item_success(client):
    """POST /sample-items 호출 시 신규 tr 행과 성공 토스트가 함께 반환되어야 한다."""
    response = client.post("/sample-items", data={"name": "테스트 추가 항목", "category": "TEST"})
    assert response.status_code == 200
    assert "테스트 추가 항목" in response.text
    assert "성공적으로 등록되었습니다" in response.text


def test_route_create_item_validation_fail(client):
    """POST /sample-items 에 빈 이름 전송 시 400 에러와 토스트 에러가 반환되어야 한다."""
    response = client.post("/sample-items", data={"name": "", "category": "TEST"})
    assert response.status_code == 400
    assert "ERR_EMPTY_NAME" in response.text


def test_route_edit_row_and_update(client):
    """수정 폼 조회 후 PUT 요청 시 데이터가 수정되어야 한다."""
    # 1. 인라인 편집 폼 조회
    edit_form_resp = client.get("/sample-items/1/edit")
    assert edit_form_resp.status_code == 200
    assert '<input type="text" name="name"' in edit_form_resp.text

    # 2. 업데이트 요청
    update_resp = client.put("/sample-items/1", data={"name": "수정완료된 항목", "category": "TECH"})
    assert update_resp.status_code == 200
    assert "수정완료된 항목" in update_resp.text
    assert SAMPLE_DB["1"]["name"] == "수정완료된 항목"


def test_route_delete_item(client):
    """DELETE /sample-items/1 호출 시 소프트 딜리트 처리되어야 한다."""
    delete_resp = client.delete("/sample-items/1")
    assert delete_resp.status_code == 200
    assert "항목이 삭제되었습니다" in delete_resp.text
    assert SAMPLE_DB["1"]["is_deleted"] is True
