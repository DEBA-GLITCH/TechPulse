from datetime import datetime
from urllib.parse import quote as url_quote

from fastapi import APIRouter, Depends, Request, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.database.crud import (
    get_latest_articles, get_top_articles, get_article_by_id,
    get_source_counts, get_last_crawl_time, get_article_count,
)
from app.core.constants import SOURCE_METADATA
from app.core.logger import app_logger
from app.crawler.collector import run_crawl

router    = APIRouter()
templates = Jinja2Templates(directory="app/templates")


# ── Jinja2 custom filters ─────────────────────────────────────────────────

def _fmt_date(dt) -> str:
    if not dt:
        return "—"
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt)
        except Exception:
            return dt
    return dt.strftime("%b %d, %Y")


def _timeago(dt) -> str:
    if not dt:
        return ""
    now  = datetime.utcnow()
    diff = (now - dt.replace(tzinfo=None)).total_seconds()
    if diff < 60:
        return "just now"
    if diff < 3_600:
        return f"{int(diff // 60)}m ago"
    if diff < 86_400:
        return f"{int(diff // 3_600)}h ago"
    return f"{int(diff // 86_400)}d ago"


templates.env.filters["fmt_date"] = _fmt_date
templates.env.filters["timeago"]  = _timeago
templates.env.filters["urlquote"] = lambda s: url_quote(str(s), safe="")


# ── Shared context helper ─────────────────────────────────────────────────

def _ctx(db: Session) -> dict:
    return {
        "source_meta":    SOURCE_METADATA,
        "source_counts":  get_source_counts(db),
        "total_articles": get_article_count(db),
        "last_crawl":     get_last_crawl_time(db),
    }


# ── Routes ────────────────────────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, source: str = None, db: Session = Depends(get_db)):
    latest = get_latest_articles(db, limit=24, source=source)
    top    = get_top_articles(db, limit=6)
    app_logger.info(f"Dashboard — {len(latest)} articles | filter={source!r}")
    return templates.TemplateResponse("index.html", {
        "request": request, "articles": latest,
        "top_articles": top, "active_source": source,
        **_ctx(db),
    })


@router.get("/article/{article_id}", response_class=HTMLResponse)
async def article_detail(request: Request, article_id: int, db: Session = Depends(get_db)):
    article = get_article_by_id(db, article_id)
    if not article:
        return HTMLResponse("<h1>404 — Not found</h1>", status_code=404)
    return templates.TemplateResponse("article.html", {
        "request": request, "article": article, **_ctx(db),
    })


@router.post("/api/crawl")
async def trigger_crawl(background_tasks: BackgroundTasks):
    app_logger.info("Manual crawl triggered")
    background_tasks.add_task(run_crawl)
    return JSONResponse({"status": "crawl_started"})


@router.get("/api/articles")
async def api_articles(limit: int = 20, source: str = None, db: Session = Depends(get_db)):
    return [a.to_dict() for a in get_latest_articles(db, limit=limit, source=source)]