from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, text

from app.database.models import Article
from app.core.logger import app_logger, error_logger

# Columns we allow to be set on the model
_MODEL_COLS = {c.name for c in Article.__table__.columns}


def upsert_article(db: Session, data: dict) -> Optional[Article]:
    """Insert new article or update summarization fields if URL already exists."""
    try:
        existing = db.query(Article).filter(Article.url == data["url"]).first()

        if existing:
            refresh_fields = {"short_summary", "key_takeaways_json", "importance_score", "raw_content", "crawled_at"}
            for field in refresh_fields:
                if field in data:
                    setattr(existing, field, data[field])
            db.commit()
            db.refresh(existing)
            app_logger.debug(f"[DB] Updated: {data['title'][:55]}")
            return existing

        safe = {k: v for k, v in data.items() if k in _MODEL_COLS}
        article = Article(**safe)
        db.add(article)
        db.commit()
        db.refresh(article)
        app_logger.info(f"[DB] Inserted: {data['title'][:55]}")
        return article

    except Exception as exc:
        db.rollback()
        error_logger.error(f"[DB] Write failure for {data.get('url', '?')[:80]}: {exc}")
        return None


def get_latest_articles(db: Session, limit: int = 20, source: Optional[str] = None) -> list[Article]:
    q = db.query(Article)
    if source:
        q = q.filter(Article.source == source)
    return q.order_by(desc(Article.crawled_at)).limit(limit).all()


def get_top_articles(db: Session, limit: int = 6) -> list[Article]:
    return (
        db.query(Article)
        .filter(Article.importance_score.isnot(None))
        .order_by(desc(Article.importance_score), desc(Article.crawled_at))
        .limit(limit)
        .all()
    )


def get_article_by_id(db: Session, article_id: int) -> Optional[Article]:
    return db.query(Article).filter(Article.id == article_id).first()


def get_last_crawl_time(db: Session) -> Optional[datetime]:
    return db.query(func.max(Article.crawled_at)).scalar()


def get_article_count(db: Session) -> int:
    return db.query(func.count(Article.id)).scalar() or 0


def get_source_counts(db: Session) -> dict[str, int]:
    rows = db.query(Article.source, func.count(Article.id)).group_by(Article.source).all()
    return {row[0]: row[1] for row in rows}


def db_is_alive(db: Session) -> bool:
    try:
        db.execute(text("SELECT 1"))
        return True
    except Exception:
        return False