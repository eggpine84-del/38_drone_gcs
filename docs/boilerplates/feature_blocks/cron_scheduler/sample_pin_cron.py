"""
[Pin-Test First] 9_cron_scheduler 핀테스트 선작성
"""
import pytest
from datetime import datetime, timezone
from docs.boilerplates.feature_blocks.cron_scheduler.core import should_execute_job


def test_cron_scheduler_due_job_should_run():
    """지정 간격(60초)이 경과한 작업은 실행 대상으로 판정되어야 한다."""
    now = datetime(2026, 10, 10, 12, 5, 0, tzinfo=timezone.utc)
    last_run = datetime(2026, 10, 10, 12, 3, 0, tzinfo=timezone.utc)  # 120초 경과

    res = should_execute_job(
        job_name="settlement_batch",
        current_time=now,
        last_run_time=last_run,
        interval_seconds=60,
        is_running=False,
    )
    assert res["success"] is True
    assert res["data"]["should_run"] is True


def test_cron_scheduler_already_running_job_blocked():
    """이전 작업이 아직 실행 중(is_running=True)인 경우 중복 실행이 차단되어야 한다."""
    now = datetime(2026, 10, 10, 12, 5, 0, tzinfo=timezone.utc)
    last_run = datetime(2026, 10, 10, 12, 0, 0, tzinfo=timezone.utc)

    res = should_execute_job(
        job_name="settlement_batch",
        current_time=now,
        last_run_time=last_run,
        interval_seconds=60,
        is_running=True,
    )
    assert res["success"] is False
    assert res["error"] == "ERR_JOB_ALREADY_RUNNING"
    assert res["data"]["should_run"] is False
