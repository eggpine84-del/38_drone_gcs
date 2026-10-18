# [파일명]: action_rule_core.py | [용도] 7대 자가 완결형 조치 수칙 순수 코어 디스패처 (외부 의존성 0건)
from typing import Dict, Any, Optional

VIOLATION_OVERWRITE = "OVERWRITE_VIOLATION"
VIOLATION_PIN_TEST_REQUIRED = "PIN_TEST_REQUIRED"
VIOLATION_PURE_CORE = "PURE_CORE_VIOLATION"
VIOLATION_DUMMY_ASSERTION = "DUMMY_ASSERTION_RED"
VIOLATION_SYNTAX_ERROR_RED = "SYNTAX_ERROR_RED"
VIOLATION_REFACTOR_TEST_MUTATION = "REFACTOR_TEST_MUTATION"
VIOLATION_SANCTUARY = "SANCTUARY_VIOLATION"

ACTION_RULE_REGISTRY: Dict[str, str] = {
    VIOLATION_OVERWRITE: (
        "조치 요령: 전체 덮어쓰기(write_to_file)는 금지됩니다. "
        "'{target_file}'의 수정할 라인만 'replace_file_content'로 교체하세요."
    ),
    VIOLATION_PIN_TEST_REQUIRED: (
        "조치 요령: '{target_file}'을 수정하기 전에, 반드시 tests/ 경로에 신규 "
        "요구사항을 검증하고 실패(Red)하는 핀-테스트를 먼저 작성하세요."
    ),
    VIOLATION_PURE_CORE: (
        "조치 요령: '{target_file}' 내 외부 I/O({modules})를 즉시 제거하세요. "
        "I/O는 shell/ 계층으로 위임하고 core/는 순수 함수로만 작성하세요."
    ),
    VIOLATION_DUMMY_ASSERTION: (
        "조치 요령: 'assert False' 같은 자해 단언문은 불인정됩니다. "
        "실제 비즈니스 함수를 호출하고 기대값과 실제값을 대조하는 진짜 단언문을 작성하세요."
    ),
    VIOLATION_SYNTAX_ERROR_RED: (
        "조치 요령: 문법/임포트 에러로 인한 실패는 불인정됩니다. "
        "호출할 함수나 클래스의 기본 스텁(빈 함수/반환값)을 먼저 선언하여 정상 호출 가능한 상태로 만드세요."
    ),
    VIOLATION_REFACTOR_TEST_MUTATION: (
        "조치 요령: 리팩토링 중에는 tests/ 내 파일 변경이 전면 금지됩니다. "
        "테스트 코드를 원복하고 오직 소스 코드의 내부 구조만 개선하세요."
    ),
    VIOLATION_SANCTUARY: (
        "조치 요령: '.agents/' 관제 파일은 사장님 사전 결재 없이 수정할 수 없습니다. "
        "수정을 중단하고 사장님께 승인을 요청하세요."
    ),
}

DEFAULT_FALLBACK_RULE = (
    "조치 요령: 감지된 아키텍처 위반 사항을 중단하고 올바른 규칙에 맞춰 수정하세요."
)


def format_action_rule(violation_type: str, context: Optional[Dict[str, Any]] = None) -> str:
    """7대 자가 완결형 조치 수칙을 안전하게 조립하는 순수 함수.
    
    외부 문서/템플릿 경로를 일절 참조하지 않고 오직 1~2줄의 명확한 행동 수칙만 반환합니다.
    """
    ctx = dict(context or {})
    target_file = ctx.get("target_file") or "대상 파일"
    modules = ctx.get("modules") or "외부 I/O 모듈"

    template = ACTION_RULE_REGISTRY.get(violation_type, DEFAULT_FALLBACK_RULE)
    try:
        return template.format(target_file=target_file, modules=modules)
    except Exception:
        return DEFAULT_FALLBACK_RULE
