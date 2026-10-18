"""
[Pin-Test First] 3_excel_io 핀테스트 선작성
"""
import pytest
from docs.boilerplates.excel_io.core import parse_csv_lines, generate_csv_text


def test_parse_csv_lines_success():
    """정상 CSV 텍스트 입력 시 헤더를 제외한 파싱된 딕셔너리 리스트를 반환해야 한다."""
    csv_raw = "name,amount\n홍길동,1000\n이순신,2000"
    valid, errors = parse_csv_lines(csv_raw)
    assert len(valid) == 2
    assert len(errors) == 0
    assert valid[0]["name"] == "홍길동"
    assert valid[0]["amount"] == 1000


def test_parse_csv_lines_with_dirty_rows():
    """빈 행이나 컬럼 누락 행은 에러 리스트로 분리 격리해야 한다."""
    csv_raw = "name,amount\n홍길동,1000\n잘못된행\n\n이순신,not_number"
    valid, errors = parse_csv_lines(csv_raw)
    assert len(valid) == 1
    assert len(errors) == 2  # 잘못된행, not_number


def test_generate_csv_text():
    """데이터 객체 리스트를 CSV 텍스트로 변환해야 한다."""
    data = [{"name": "홍길동", "amount": 1000}]
    csv_out = generate_csv_text(data, ["name", "amount"])
    assert "name,amount" in csv_out
    assert "홍길동,1000" in csv_out
