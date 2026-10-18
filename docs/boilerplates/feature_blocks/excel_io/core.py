"""
[Core] CSV / 엑셀 대량 입출력 순수 처리 함수
"""
import io
import csv
from typing import List, Dict, Any, Tuple


def parse_csv_lines(raw_text: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """CSV 원시 텍스트를 파싱하여 정상 행과 비정상 행을 격리 분리한다."""
    valid_rows: List[Dict[str, Any]] = []
    error_rows: List[Dict[str, Any]] = []

    if not raw_text or not raw_text.strip():
        return valid_rows, error_rows

    reader = csv.reader(io.StringIO(raw_text.strip()))
    header = None

    for idx, row in enumerate(reader):
        if not row or not any(field.strip() for field in row):
            continue  # 빈 줄 건너뜀

        if header is None:
            header = [col.strip() for col in row]
            continue

        if len(row) != len(header):
            error_rows.append({"line": idx + 1, "raw": row, "reason": "ERR_COLUMN_COUNT_MISMATCH"})
            continue

        row_dict = dict(zip(header, [col.strip() for col in row]))

        # 필수 필드 유효성 검증 예시
        amount_raw = row_dict.get("amount", "0")
        try:
            row_dict["amount"] = int(amount_raw)
            valid_rows.append(row_dict)
        except ValueError:
            error_rows.append({"line": idx + 1, "raw": row, "reason": "ERR_INVALID_NUMBER"})

    return valid_rows, error_rows


def generate_csv_text(records: List[Dict[str, Any]], headers: List[str]) -> str:
    """딕셔너리 리스트를 CSV 문자열로 변환한다."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    for r in records:
        writer.writerow([r.get(h, "") for h in headers])
    return output.getvalue()
