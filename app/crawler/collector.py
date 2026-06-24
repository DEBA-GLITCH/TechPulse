"""
Main crawl orchestrator — runs all sources, persists results.
"""
import asyncio
import json
import time
from datetime import datetime
from typing import Optional

import httpx

from app.core.config import settings
from app.core.constants import SOURCE_METADATA, REQUEST_HEADERS
from app.core.logger import crawler_logger, error_logger
from app.crawler.sources import SOURCE_PARSERS
from app.crawler.extractor import extract_content, extract_og_title
from app.database.session import SessionLocal
from app.database.crud import upsert_article
from app.summarizer.groq_client import summarize_article


async def _fetch(client: httpx.AsyncClient, url: str) -> Optional[str]:
    try:
        r = await client.get(url, timeout=settings.REQUEST_TIMEOUT, follow_redirects=True)
        r.raise_for_status()
        return r.text
    except httpx.TimeoutException:
        error_logger.error(f"[TIMEOUT] {url}")
    except httpx.HTTPStatusError as exc:
        error_logger.error(f"[HTTP {exc.response.status_code}] {url}")
    except httpx.RequestError as exc:
        error_logger.error(f"[REQUEST ERROR] {url} — {exc}")
    return None


async def _process_source(client: httpx.AsyncClient, name: str, meta: dict, db) -> int:
    crawler_logger.info(f"┌─ [{name}] crawling {meta['url']}")
    t0 = time.monotonic()

    listing_html = await _fetch(client, meta["url"])
    if not listing_html:
        crawler_logger.warning(f"└─ [{name}] no HTML — skipping")
        return 0

    parser = SOURCE_PARSERS.get(name)
    if not parser:
        crawler_logger.warning(f"└─ [{name}] no parser registered")
        return 0

    stubs = parser(listing_html)
    crawler_logger.info(f"│  [{name}] {len(stubs)} stubs found")

    saved = 0
    for stub in stubs[: settings.MAX_ARTICLES_PER_SOURCE]:
        try:
            article_html = await _fetch(client, stub["url"])
            content      = extract_content(article_html or "", stub["url"])
            title        = (extract_og_title(article_html or "") if article_html else None) or stub["title"]

            summary = {}
            if content:
                summary = await summarize_article(title=title, content=content, source=name)
            else:
                crawler_logger.warning(f"│  [{name}] empty content — {stub['url'][:60]}")

            record = {
                "title":              title,
                "url":                stub["url"],
                "source":             name,
                "published_at":       stub.get("published_at"),
                "raw_content":        content[:8_000] if content else None,
                "short_summary":      summary.get("short_summary"),
                "key_takeaways_json": json.dumps(summary.get("key_takeaways", [])),
                "importance_score":   summary.get("importance_score", 5),
                "crawled_at":         datetime.utcnow(),
            }

            if upsert_article(db, record):
                saved += 1

            await asyncio.sleep(1.2)  # polite delay

        except Exception as exc:
            error_logger.error(f"│  [{name}] error processing {stub.get('url','?')[:60]}: {exc}")

    elapsed = time.monotonic() - t0
    crawler_logger.info(f"└─ [{name}] done — {saved} saved in {elapsed:.1f}s")
    return saved


async def run_crawl() -> dict:
    crawler_logger.info("=" * 64)
    crawler_logger.info("CRAWL CYCLE STARTED")
    crawler_logger.info("=" * 64)

    results: dict[str, dict] = {}
    db = SessionLocal()

    try:
        async with httpx.AsyncClient(headers=REQUEST_HEADERS) as client:
            for name, meta in SOURCE_METADATA.items():
                try:
                    n = await _process_source(client, name, meta, db)
                    results[name] = {"status": "ok", "saved": n}
                except Exception as exc:
                    error_logger.error(f"[FATAL] {name}: {exc}")
                    results[name] = {"status": "error", "error": str(exc)}
                await asyncio.sleep(2.5)
    finally:
        db.close()

    total = sum(v.get("saved", 0) for v in results.values())
    crawler_logger.info(f"CRAWL COMPLETE — total saved: {total}")
    crawler_logger.info("=" * 64)
    return {"results": results, "total_saved": total, "timestamp": datetime.utcnow().isoformat()}