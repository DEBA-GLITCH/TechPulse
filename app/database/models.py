import json
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, func
from app.database.session import Base


class Article(Base):
    __tablename__ = "articles"

    id                 = Column(Integer, primary_key=True, index=True)
    title              = Column(String(600),  nullable=False)
    url                = Column(String(2000), unique=True, nullable=False, index=True)
    source             = Column(String(120),  nullable=False, index=True)
    published_at       = Column(DateTime, nullable=True)
    raw_content        = Column(Text,     nullable=True)
    short_summary      = Column(Text,     nullable=True)
    key_takeaways_json = Column(Text,     nullable=True)   # JSON array string
    importance_score   = Column(Integer,  nullable=True, default=5)
    crawled_at         = Column(DateTime, default=func.now())
    created_at         = Column(DateTime, default=func.now())

    # --- Python-level helpers (not DB columns) ---

    @property
    def key_takeaways(self) -> list[str]:
        if not self.key_takeaways_json:
            return []
        try:
            return json.loads(self.key_takeaways_json)
        except (json.JSONDecodeError, TypeError):
            return []

    @property
    def display_date(self) -> datetime | None:
        return self.published_at or self.crawled_at

    def to_dict(self) -> dict:
        return {
            "id":               self.id,
            "title":            self.title,
            "url":              self.url,
            "source":           self.source,
            "published_at":     self.published_at.isoformat() if self.published_at else None,
            "short_summary":    self.short_summary,
            "key_takeaways":    self.key_takeaways,
            "importance_score": self.importance_score,
            "crawled_at":       self.crawled_at.isoformat() if self.crawled_at else None,
        }