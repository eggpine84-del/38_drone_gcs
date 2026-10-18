"""
[Shell] 경량 스케줄러 상태 조회 및 수동 트리거 라우트 (FastAPI)
"""
from datetime import datetime, timezone
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from docs.boilerplates.feature_blocks.cron_scheduler.core import should_execute_job

router = APIRouter(prefix="/sample-cron", tags=["sample-cron"])

# 인메모리 스케줄 상태 (실무에서는 DB 테이블 기반 분산 락/로그 관리)
SCHEDULE_STATE = {
    "last_run_time": None,
    "is_running": False,
    "interval_seconds": 300,  # 5분 주기
}


@router.post("/trigger")
async def trigger_job_endpoint():
    """배치 작업 수동 트리거 및 실행 판정 Shell."""
    now = datetime.now(timezone.utc)
    res = should_execute_job(
        job_name="settlement_daily_batch",
        current_time=now,
        last_run_time=SCHEDULE_STATE["last_run_time"],
        interval_seconds=SCHEDULE_STATE["interval_seconds"],
        is_running=SCHEDULE_STATE["is_running"],
    )

    if not res["success"]:
        return JSONResponse(status_code=409, content={"success": False, "error": res["error"]})

    if res["data"]["should_run"]:
        SCHEDULE_STATE["is_running"] = True
        try:
            # 실제 배치 작업 수행 구역
            SCHEDULE_STATE["last_run_time"] = now
        finally:
            SCHEDULE_STATE["is_running"] = False
        return JSONResponse(status_code=200, content={"success": True, "message": "배치 작업 성공"})

    return JSONResponse(status_code=200, content={"success": True, "message": "주기 미도달로 스킵"})
