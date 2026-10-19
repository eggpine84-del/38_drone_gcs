# -*- coding: utf-8 -*-
# [파일명]: main.py (대장 템플릿 - 유니버설 올인원 실행 파일)
# [원칙] 1. 기승전결 구역 준수 | 2. 웹서버/크론/워크플로우 3대 모드 일체형 디스패치 | 3. 무터치 DB 보존 헌법
# [SYSTEM] Senior Staff Engineer (Google/Amazon) - Safe, Readable, Scalable Code.
import asyncio
from contextlib import asynccontextmanager
import logging
import os
import sys
import time
from typing import Any, Dict, Optional, Tuple

# [1. 기(起) 구역 - 환경 및 방탄 로깅 설정]
LOG_FILE_PATH = "logs/main_system.log"
ERR_VAL_CODE, ERR_VAL_MSG = "VAL_ERR_01", "입력 데이터가 올바르지 않거나 비어 있습니다."
ERR_SYSTEM_CODE = "SYS_ERR_99"
os.makedirs(os.path.dirname(LOG_FILE_PATH), exist_ok=True)  # 로그 폴더 자동 생성 방어 코드
logging.basicConfig(filename=LOG_FILE_PATH, level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
default_logger = logging.getLogger("UniversalMain")


async def log_error(code: str, message: str, logger: logging.Logger = default_logger) -> None:
    """Logs system errors safely. Args: code(str), message(str), logger(logging.Logger)."""
    logger.error(f"[{code}] {message}")  # [요약] 프로그램 에러를 외부에서 주입받은 로거 메모장에 안전하게 기록합니다!


# [2. 승(承) 구역 - 문지기 입력 검증 (T1 Input Distrust)]
async def validate_and_prepare_input(raw_data: Optional[Dict[str, Any]]) -> Tuple[bool, Optional[Dict[str, Any]], str]:
    """Validates runtime input type and null safety."""
    if not isinstance(raw_data, dict):
        await log_error(ERR_VAL_CODE, ERR_VAL_MSG)
        return False, None, ERR_VAL_MSG  # 에러 기록 누락 방지
    return True, raw_data, "검증 통과"  # [요약] 들어온 데이터가 올바른 딕셔너리인지 꼼꼼히 검증합니다!


# [3. 전(轉) 구역 - 비즈니스 조율 핵심 로직]
async def process_core_behavior(validated_data: Dict[str, Any]) -> Dict[str, Any]:
    """Executes business operations asynchronously by delegating to Pure Core."""
    try:
        # 실무에서는 여기서 core/ 모듈의 순수 함수를 호출하여 비즈니스 연산을 위임합니다.
        return {"success": True, "result": {**validated_data, "processed_at": time.strftime("%Y-%m-%d %H:%M:%S")}, "error": ""}
    except Exception as e:
        await log_error(ERR_SYSTEM_CODE, f"핵심 로직 실행 중 오류 발생: {e}")
        return {"success": False, "result": None, "error": f"핵심 로직 실행 중 오류 발생: {e}"}


# [4. 결(結) 구역 - 비동기/동기 유니버설 인터페이스]
async def run_main_workflow(raw_input: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Coordinates the entire workflow lifecycle (Async Native)."""
    is_valid, clean_data, error_message = await validate_and_prepare_input(raw_input)
    if not is_valid:
        return {"success": False, "result": None, "error": error_message}
    return await process_core_behavior(clean_data)


def run_main_workflow_sync(raw_input: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Provides a synchronous wrapper for legacy, CLI, or cron environments."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop and loop.is_running():
        raise RuntimeError("이미 이벤트 루프가 돌고 있습니다. await run_main_workflow()를 사용하세요.")
    return asyncio.run(run_main_workflow(raw_input))


# [5. 웹 서버 수명주기 헌법 - 무터치(Zero-Touch) DB 보존 & FastAPI 앱]
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from src.engine.shell.telemetry_routes import router as telemetry_router
from src.engine.shell.failsafe_routes import router as failsafe_router
from src.features.dashboard.shell.dashboard_routes import router as dashboard_router
from src.features.geofence.shell.geofence_routes import router as geofence_router
from src.features.mission.shell.mission_routes import router as mission_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    from src.engine.shell.db_schema import init_db
    from src.engine.shell.config import get_config
    from src.engine.shell.drone_gcs_service import DroneGCSService
    from src.engine.shell.drone_repository import SqliteDroneLedgerRepository
    from src.engine.shell.mavlink_receiver import MAVLinkReceiver

    init_db()

    cfg = get_config()
    worker_task = None
    receiver = None
    stop_event = asyncio.Event()

    if cfg.mavlink_enabled:
        from src.engine.core.mavlink_parser_core import parse_connection_strings_core
        from src.engine.shell.mavlink_receiver import MAVLinkMultiReceiver

        service = DroneGCSService(repository=SqliteDroneLedgerRepository())
        conns = parse_connection_strings_core(cfg.mavlink_connection_string)
        if len(conns) > 1:
            receiver = MAVLinkMultiReceiver(
                service=service,
                connection_strings=conns,
                default_drone_id=cfg.default_drone_id,
                auto_detect_sysid=True,
            )
        else:
            receiver = MAVLinkReceiver(
                drone_id=cfg.default_drone_id,
                service=service,
                connection_string=conns[0] if conns else cfg.mavlink_connection_string,
                auto_detect_sysid=True,
            )

        # 활성 MAVLink 통신 소켓을 웹 비행 제어 명령 서비스에 직결
        from src.features.dashboard.shell.flight_command_service import get_flight_command_service
        get_flight_command_service().set_connection(receiver.connection)

        async def _mavlink_worker():
            while not stop_event.is_set():
                try:
                    await asyncio.to_thread(receiver.poll_once)
                    await asyncio.sleep(0.02)
                except asyncio.CancelledError:
                    break
                except Exception:
                    await asyncio.sleep(0.1)

        worker_task = asyncio.create_task(_mavlink_worker())

    try:
        yield
    finally:
        from src.features.dashboard.shell.flight_command_service import get_flight_command_service
        get_flight_command_service().set_connection(None)

        if worker_task:
            stop_event.set()
            worker_task.cancel()
            try:
                await worker_task
            except asyncio.CancelledError:
                pass
        if receiver:
            receiver.close()


app = FastAPI(title="Drone-GCS Control Center", lifespan=lifespan)
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(dashboard_router)
app.include_router(geofence_router)
app.include_router(mission_router)
app.include_router(telemetry_router)
app.include_router(failsafe_router)


# =============================================================================
# [6. 유니버설 실행 디스패처 - 3대 모드 자동 감지]
# =============================================================================
if __name__ == "__main__":
    # --- [모드 1]: 웹 서버 모드 (FastAPI/Uvicorn 자동 감지) ---
    _app = globals().get("app")
    if _app:
        print("= [웹 서버 모드] Uvicorn 엔진 가동 시작 (무터치 DB 보존 모드) =")
        import uvicorn
        uvicorn.run(_app, host="127.0.0.1", port=8000)
        sys.exit(0)

    # --- [모드 2]: 단발성 크론/배치 스크립트 모드 (--cron 인자 시) ---
    if "--cron" in sys.argv:
        print("= [히트 앤드 런] 단발성 크론 배치 가동 =")
        t_start = time.time()
        job_payload = {"task": "scheduled_batch", "trigger": "cron"}
        result = run_main_workflow_sync(job_payload)
        t_elapsed = time.time() - t_start
        print(f"  -> 완료 소요시간: {t_elapsed:.2f}초 | 결과: {result.get('success')}")
        sys.exit(0 if result.get("success") else 1)

    # --- [모드 3]: 유니버설 비동기/동기 모듈 단독 자가 검증 테스트 ---
    print("= [유니버설 메인] 기승전결 단독 자가 검증 테스트 =")
    async def _run_self_tests():
        res_suc, res_fail = await asyncio.gather(
            run_main_workflow({"test_key": "async_val"}),
            run_main_workflow(None)
        )
        assert res_suc.get("success") is True, "비동기 성공 케이스 실패"
        assert res_fail.get("success") is False, "비동기 실패 케이스 누락"
        print("  [*] 1. 비동기(Async) Native 파이프라인 검증 통과")
    asyncio.run(_run_self_tests())

    sync_suc = run_main_workflow_sync({"test_key": "sync_val"})
    sync_fail = run_main_workflow_sync(None)
    assert sync_suc.get("success") is True, "동기 성공 브릿지 실패"
    assert sync_fail.get("success") is False, "동기 실패 브릿지 누락"
    print("  [*] 2. 동기(Sync) Bridge 파이프라인 검증 통과")
    print("  [*] 3. 웹서버/크론/비동기 올인원 유니버설 규격 확인 완료.")
