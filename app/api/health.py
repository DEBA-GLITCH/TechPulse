from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.database.crud import get_last_crawl_time, get_article_count, db_is_alive, get_source_counts
from app.core.config import settings
from app.core.logger import app_logger

router = APIRouter(tags=["ops"])


@router.get("/health")
async def health(db: Session = Depends(get_db)):
    db_ok      = db_is_alive(db)
    last_crawl = get_last_crawl_time(db)
    count      = get_article_count(db)
    sources    = get_source_counts(db)

    status = "ok" if db_ok else "degraded"
    app_logger.debug(f"/health → {status}")

    return {
        "status":           status,
        "app":              settings.APP_NAME,
        "version":          settings.APP_VERSION,
        "api_status":       "ok",
        "database_status":  "ok" if db_ok else "error",
        "last_crawl_utc":   last_crawl.isoformat() if last_crawl else None,
        "article_count":    count,
        "source_breakdown": sources,
        "timestamp_utc":    datetime.utcnow().isoformat(),
    }