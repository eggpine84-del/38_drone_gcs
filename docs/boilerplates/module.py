# [파일명]: module.py (순수 연산 코어 템플릿 - Pure Functional Core) | [원칙] 100% Pure Function, I/O 부작용 0건, 12세 수준 요약 주석 필수
# [SYSTEM] Senior Staff Engineer - Pure Core Standard (FCIS / T0~T2 준수).
from typing import Any, Dict, Optional, Tuple

ERR_VAL_CODE, ERR_VAL_MSG = "VAL_ERR_01", "입력 데이터가 올바르지 않거나 비어 있습니다."


def validate_and_prepare_input(raw_data: Optional[Dict[str, Any]]) -> Tuple[bool, Optional[Dict[str, Any]], str]:
    """런타임 입력값의 타입과 무결성을 100% 불신하고 검증하는 순수 함수 (T1 준수)."""
    if not isinstance(raw_data, dict) or not raw_data:
        return False, None, ERR_VAL_MSG
    return True, raw_data, "검증 통과"
    # [요약] 외부에서 들어온 상자가 찌그러지거나 비어있지 않은지 문지기처럼 꼼꼼하게 확인했습니다!


def process_core_behavior(validated_data: Dict[str, Any]) -> Dict[str, Any]:
    """부작용(Side-Effect) 없이 입력값만을 기반으로 새로운 결과를 계산하는 결정론적 순수 함수 (T0/T2 준수)."""
    computed_result = {
        **validated_data,
        "is_processed": True,
        "item_count": len(validated_data)
    }
    return {"success": True, "result": computed_result, "error": ""}
    # [요약] 들어온 원래 상자를 망가뜨리지 않고 복사해서 필요한 계산만 깔끔하게 끝마쳤습니다!


def execute_pure_logic(raw_input: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """입력 검증과 순수 연산을 결합하여 결정론적 결과를 도출하는 코어 파사드 순수 함수."""
    is_valid, clean_data, error_message = validate_and_prepare_input(raw_input)
    if not is_valid or clean_data is None:
        return {"success": False, "result": None, "error": error_message}
    return process_core_behavior(clean_data)
    # [요약] 문지기 통과부터 계산 완료까지 순수한 연산 과정 전체를 질서정연하게 지휘했습니다!


# ================= (FCIS 100% Pure Core 단독 검증 구역) =================
if __name__ == "__main__":
    print("= [FCIS 순수 코어] 단독 가동 테스트 =")
    res_suc = execute_pure_logic({"sample_key": "sample_value"})
    res_fail = execute_pure_logic(None)
    res_empty = execute_pure_logic({})

    assert res_suc["success"] is True
    assert res_suc["result"]["is_processed"] is True
    assert res_fail["success"] is False
    assert res_empty["success"] is False
    print("  - 입력 검증 및 순수 연산 무결성 100% 통과")
    print("모든 FCIS Pure Core 테스트가 성공적으로 완료되었습니다.")