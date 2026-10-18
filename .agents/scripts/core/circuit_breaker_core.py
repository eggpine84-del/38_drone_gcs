# [파일명]: circuit_breaker_core.py | [용도] 테스트 실패 시 하이브리드 JSON 지능형 피드백 생성 및 서킷 브레이커(자동 롤백) 관리
import os
import re
import json
import subprocess
from typing import Optional, List, Tuple, Dict


def parse_test_failure_hybrid(
    raw_output: str,
    dirty_sources: Optional[List[str]] = None,
    current_retry: int = 1,
    max_retries: int = 3,
    failed_count_info: str = ""
) -> str:
    """pytest 원시 출력에서 첫 번째 실패 1개만 레이저 타격하여 하이브리드 JSON 피드백을 생성하는 순수 함수 (2중 안전 폴백 내장)."""
    try:
        # 1. 첫 번째 FAILED 패턴 추출
        failed_match = re.search(r"FAILED\s+([^\s\n]+)", raw_output)
        failed_test = failed_match.group(1).strip() if failed_match else "unknown_test"

        # 2. 첫 번째 단언문(assert) 또는 에러 원인 추출
        assert_match = re.search(r"(AssertionError:[^\n]+|assert[^\n]+|E\s+[^\n]+)", raw_output)
        if assert_match:
            failed_assert = assert_match.group(1).strip()
            if failed_assert.startswith("E "):
                failed_assert = failed_assert[2:].strip()
        else:
            failed_assert = "단언문 불일치 또는 런타임 예외 발생"

        # 3. 타깃 파일 목록
        targets = dirty_sources if dirty_sources else []

        payload = {
            "status": f"FAILED ({failed_count_info})" if failed_count_info else "FAILED",
            "current_target": failed_test,
            "failed_assert": failed_assert,
            "target_files": targets,
            "instruction": (
                "테스트 코드는 절대 수정할 수 없습니다. "
                "target_files의 비즈니스/뷰 렌더링 코드에서 위 단언 규격을 충족하거나, "
                "해결 불가능 시 즉시 'git restore <대상파일>'을 실행하십시오."
            ),
            "retry_status": f"{current_retry} / {max_retries}회 시도 중"
        }

        json_str = json.dumps(payload, ensure_ascii=False, indent=2)
        guidance = (
            f"[테스트 게이트 차단: All-Pass 엄격 기준 위반]\n\n"
            f"```json\n{json_str}\n```\n\n"
            f"[행동 강제] 사장님께 승인을 묻거나 선택지를 나열하는 질문은 시스템에 의해 전면 거부됩니다. "
            f"즉시 위 target_files를 핀포인트 수정하거나 원복하십시오."
        )
        return guidance
    except Exception:
        # 2중 안전 폴백: 파싱 실패 시 원시 텍스트 반환
        return raw_output


def evaluate_circuit_breaker_state(
    counter_dir: str,
    failed_signature: str,
    max_retries: int = 3
) -> Tuple[Dict, int, bool]:
    """동일 실패 반복 여부를 감지하여 연속 실패 시 카운트를 올리고, 실패 대상 변경 시(진전) 리셋하는 순수 상태 평가 함수."""
    counter_file = os.path.join(counter_dir, ".retry_counter.json")
    state = {"last_failed": "", "count": 0}

    if os.path.exists(counter_file):
        try:
            with open(counter_file, "r", encoding="utf-8") as f:
                state = json.load(f)
        except Exception:
            pass

    last_failed = state.get("last_failed", "")
    current_count = state.get("count", 0)

    if last_failed == failed_signature:
        current_count += 1
    else:
        # 실패 대상이 변경됨 (진전 감지) ➔ 1로 리셋
        last_failed = failed_signature
        current_count = 1

    is_tripped = (current_count >= max_retries)
    state = {"last_failed": last_failed, "count": current_count}

    try:
        with open(counter_file, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False)
    except Exception:
        pass

    return state, current_count, is_tripped


def reset_circuit_breaker(counter_dir: str) -> None:
    """테스트 통과 시 서킷 브레이커 카운터를 원자적으로 삭제 및 리셋하는 함수."""
    counter_file = os.path.join(counter_dir, ".retry_counter.json")
    if os.path.exists(counter_file):
        try:
            os.remove(counter_file)
        except Exception:
            pass


def handle_test_failure_orchestration(
    project_root: str,
    runner_name: str,
    returncode: int,
    stdout_and_stderr: str,
    changed_files: List[str],
    guard_config: Dict,
    extract_dirty_sources_fn=None
) -> str:
    """테스트 실패 시 서킷 브레이커 상태 갱신, 강제 롤백 판정, 하이브리드 JSON 피드백 생성을 총괄하는 순수 오케스트레이션 함수."""
    dirty_sources = extract_dirty_sources_fn(changed_files) if extract_dirty_sources_fn else []
    counter_dir = os.path.join(project_root, ".agents")

    cb_cfg = guard_config.get("circuit_breaker_policy", {})
    is_cb_enabled = guard_config.get("switches", {}).get("enable_circuit_breaker", True)
    max_retries = cb_cfg.get("max_retries", 3)

    # 1. 실패 서명(Signature) 추출 (실패 대상 변경 감지용)
    failed_match = re.search(r"FAILED\s+([^\s\n]+)", stdout_and_stderr)
    failed_sig = failed_match.group(1).strip() if failed_match else runner_name

    current_retry = 1
    is_tripped = False
    if is_cb_enabled:
        _, current_retry, is_tripped = evaluate_circuit_breaker_state(
            counter_dir=counter_dir,
            failed_signature=failed_sig,
            max_retries=max_retries
        )

    # 2. 서킷 브레이커 발동(3회 연속 실패) 시 자동 안전 롤백 실행
    if is_tripped:
        reset_circuit_breaker(counter_dir)
        try:
            subprocess.run(
                ["git", "restore"] + (dirty_sources if dirty_sources else ["."]),
                cwd=project_root,
                capture_output=True,
                text=True,
                timeout=5
            )
            subprocess.run(["git", "clean", "-f"], cwd=project_root, capture_output=True, timeout=5)
        except Exception:
            pass
        return (
            f"[서킷 브레이커 발동: {max_retries}회 연속 실패로 인한 안전 강제 원복]\n"
            f"대상 '{failed_sig}'에서 {max_retries}회 연속 실패하여 무한루프 차단을 위해 작업 트리를 'git restore'로 자동 원복했습니다.\n"
            f"사장님 직언 보고: 실패 단언을 해결할 수 없는 아키텍처/테스트 모순 상태입니다. 사장님의 수동 개입이 필요합니다."
        )

    # 3. 정상 피드백: 정밀 하이브리드 JSON 피드백 조립
    return parse_test_failure_hybrid(
        raw_output=stdout_and_stderr,
        dirty_sources=dirty_sources,
        current_retry=current_retry,
        max_retries=max_retries
    )
