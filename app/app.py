import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.config import settings
from app.core.logger import app_logger
from app.database.session import Base, engine
from app.api.routes import router as web_router
from app.api.health import router as health_router
from app.crawler.collector import run_crawl

scheduler = AsyncIOScheduler(timezone="UTC")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # ── Startup ──────────────────────────────────────────────────────────
    app_logger.info(f"{'='*56}")
    app_logger.info(f"  {settings.APP_NAME} v{settings.APP_VERSION} — starting")
    app_logger.info(f"{'='*56}")

    Base.metadata.create_all(bind=engine)
    app_logger.info("Database schema ready")

    scheduler.add_job(
        run_crawl, trigger="interval",
        hours=settings.CRAWL_INTERVAL_HOURS,
        id="periodic_crawl", replace_existing=True,
    )
    scheduler.start()
    app_logger.info(f"Scheduler armed — crawl every {settings.CRAWL_INTERVAL_HOURS}h")

    # Fire initial crawl in background so server starts immediately
    asyncio.create_task(run_crawl())
    app_logger.info("Initial crawl task queued")

    yield

    # ── Shutdown ─────────────────────────────────────────────────────────
    scheduler.shutdown(wait=False)
    app_logger.info(f"{settings.APP_NAME} shut down cleanly")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url=None,
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.include_router(health_router)
app.include_router(web_router)