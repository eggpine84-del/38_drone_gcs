# -*- coding: utf-8 -*-
# [파일명]: main.py (드론 GCS 웹서버 엔트리포인트 - 순수 오케스트레이터)
# [원칙] 1. 단일 책임(SRP) 및 120줄 이하 엄수 | 2. 5대 라우터 수집 및 수명주기 전담 | 3. 비즈니스 로직 0건
# [SYSTEM] Senior Staff Engineer (Google/Amazon) - Safe, Readable, Scalable Code.
import asyncio
from contextlib import asynccontextmanager
import logging
import os
import sys

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from src.engine.shell.failsafe_routes import router as failsafe_router
from src.engine.shell.telemetry_routes import router as telemetry_router
from src.features.dashboard.shell.dashboard_routes import router as dashboard_router
from src.features.geofence.shell.geofence_routes import router as geofence_router
from src.features.mission.shell.mission_routes import router as mission_router

# [1. 시스템 방탄 로깅 설정]
LOG_FILE_PATH = "logs/main_system.log"
os.makedirs(os.path.dirname(LOG_FILE_PATH), exist_ok=True)
logging.basicConfig(
    filename=LOG_FILE_PATH,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("DroneGCSMain")


# [2. 웹서버 및 MAVLink 통신 수명주기 헌법]
@asynccontextmanager
async def lifespan(app: FastAPI):
    from src.engine.shell.config import get_config
    from src.engine.shell.db_schema import init_db
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


# [3. FastAPI 앱 생성 및 5대 라우터 등록]
app = FastAPI(title="Drone-GCS Control Center", lifespan=lifespan)
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(dashboard_router)
app.include_router(geofence_router)
app.include_router(mission_router)
app.include_router(telemetry_router)
app.include_router(failsafe_router)


# [4. 웹 서버 실행 엔트리포인트]
if __name__ == "__main__":
    import uvicorn
    logger.info("Drone-GCS Uvicorn 웹 서버 가동")
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False)

