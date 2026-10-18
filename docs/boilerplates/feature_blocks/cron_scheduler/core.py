"""
[Core] 경량 스케줄러 실행 주기 및 중복 실행 락 판정 순수 모듈 (FCIS Pure Core)
"""
from datetime import datetime
from typing import Dict, Any, TypedDict, Optional


class SchedulerResult(TypedDict):
    success: bool
    data: Optional[Dict[str, Any]]
    error: Optional[str]


def should_execute_job(
    job_name: str,
    current_time: datetime,
    last_run_time: Optional[datetime],
    interval_seconds: int,
    is_running: bool,
) -> SchedulerResult:
    """작업 실행 대상 여부 및 중복 실행 락을 순수 판정한다."""
    if not job_name:
        return {"success": False, "data": None, "error": "ERR_INVALID_JOB_NAME"}
    if interval_seconds <= 0:
        return {"success": False, "data": None, "error": "ERR_INVALID_INTERVAL"}

    # 1. 이전 작업이 아직 실행 중이면 즉시 중복 실행 차단 (락 보호)
    if is_running:
        return {
            "success": False,
            "data": {"should_run": False, "reason": "ALREADY_RUNNING"},
            "error": "ERR_JOB_ALREADY_RUNNING",
        }

    # 2. 최초 실행인 경우 즉시 실행 대상
    if last_run_time is None:
        return {
            "success": True,
            "data": {"should_run": True, "job_name": job_name},
            "error": None,
        }

    # 3. 경과 시간 계산 및 주기 도달 여부 판정
    elapsed = (current_time - last_run_time).total_seconds()
    if elapsed >= interval_seconds:
        return {
            "success": True,
            "data": {"should_run": True, "job_name": job_name, "elapsed_seconds": elapsed},
            "error": None,
        }

    return {
        "success": True,
        "data": {
            "should_run": False,
            "job_name": job_name,
            "remaining_seconds": max(0.0, interval_seconds - elapsed),
        },
        "error": None,
    }
