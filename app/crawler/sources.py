"""
Per-source HTML parsers.
Each returns: list[dict]  →  {title, url, published_at: datetime | None}
"""
import json
import re
from datetime import datetime
from typing import Optional
from bs4 import BeautifulSoup, Tag

from app.core.logger import crawler_logger


# ---------------------------------------------------------------------------
# Date helpers
# ---------------------------------------------------------------------------

_DATE_FMTS = [
    "%B %d, %Y", "%b %d, %Y", "%Y-%m-%d", "%d %B %Y",
    "%d %b %Y", "%Y/%m/%d", "%B %Y", "%b %Y",
]
_DATE_RE = re.compile(
    r"(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?"
    r"|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
    r"\s+\d{1,2},?\s+\d{4}",
    re.IGNORECASE,
)


def _parse_date(raw: str) -> Optional[datetime]:
    if not raw:
        return None
    raw = raw.strip()
    for fmt in _DATE_FMTS:
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            pass
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00").split("+")[0])
    except ValueError:
        pass
    return None


def _nearest_date(el: Tag) -> Optional[datetime]:
    """Walk up from a tag trying to find a date string nearby."""
    container = el.find_parent(["article", "li", "div", "section"])
    if not container:
        return None
    time_tag = container.find("time")
    if time_tag:
        raw = time_tag.get("datetime") or time_tag.get_text(strip=True)
        return _parse_date(raw)
    m = _DATE_RE.search(container.get_text())
    return _parse_date(m.group(0)) if m else None


# ---------------------------------------------------------------------------
# Parsers
# ---------------------------------------------------------------------------

def parse_openai(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    articles: list[dict] = []

    # Strategy 1 — Next.js __NEXT_DATA__
    script = soup.find("script", {"id": "__NEXT_DATA__"})
    if script and script.string:
        try:
            data = json.loads(script.string)
            pp = data.get("props", {}).get("pageProps", {})
            posts = pp.get("posts") or pp.get("articles") or pp.get("items") or []
            for p in posts:
                title = p.get("title") or p.get("name", "")
                slug  = p.get("slug") or p.get("id") or ""
                url   = (
                    slug if slug.startswith("http")
                    else f"https://openai.com/index/{slug}" if slug else ""
                )
                if title and url:
                    articles.append({
                        "title":        title,
                        "url":          url,
                        "published_at": _parse_date(p.get("publishedAt") or p.get("date", "")),
                    })
            if articles:
                crawler_logger.info(f"[OpenAI] {len(articles)} articles from __NEXT_DATA__")
                return articles[:10]
        except Exception as e:
            crawler_logger.warning(f"[OpenAI] __NEXT_DATA__ failed: {e}")

    # Strategy 2 — Static link scan
    seen: set[str] = set()
    skip = {"/api/", "/cdn-", "#", "/policies", "/about", "/pricing", "/careers", "/safety"}
    for a in soup.select("a[href]"):
        href: str = a.get("href", "")
        if href.startswith("/"):
            href = "https://openai.com" + href
        if not href.startswith("https://openai.com"):
            continue
        if any(s in href for s in skip):
            continue
        if href in seen:
            continue
        title = a.get_text(strip=True)
        if len(title) < 15:
            continue
        seen.add(href)
        articles.append({"title": title, "url": href, "published_at": _nearest_date(a)})

    crawler_logger.info(f"[OpenAI] {len(articles)} articles via HTML scan")
    return articles[:10]


def parse_anthropic(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    articles: list[dict] = []
    seen: set[str] = set()
    skip = {"/company", "/about", "/careers", "/research#", "/privacy", "?", "#", "/404"}

    for a in soup.select("a[href]"):
        href: str = a.get("href", "")
        if href.startswith("/"):
            href = "https://www.anthropic.com" + href
        if "anthropic.com" not in href:
            continue
        if any(s in href for s in skip):
            continue
        if "/news/" not in href and "/research/" not in href:
            continue
        if href in seen:
            continue

        title = a.get_text(strip=True)
        # Title might be in a sibling / parent heading
        if len(title) < 10:
            parent = a.find_parent(["article", "li", "div"])
            if parent:
                h = parent.find(["h2", "h3", "h4"])
                if h:
                    title = h.get_text(strip=True)

        if len(title) < 10:
            continue

        seen.add(href)
        articles.append({"title": title, "url": href, "published_at": _nearest_date(a)})

    crawler_logger.info(f"[Anthropic] {len(articles)} articles")
    return articles[:10]


def parse_huggingface(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    articles: list[dict] = []
    seen: set[str] = set()
    blog_root = "https://huggingface.co/blog"

    for a in soup.select("a[href*='/blog/']"):
        href: str = a.get("href", "")
        if href.startswith("/"):
            href = "https://huggingface.co" + href
        if not href.startswith(blog_root):
            continue
        if href.rstrip("/") == blog_root:
            continue
        if href in seen:
            continue

        title = a.get_text(strip=True)
        if not title or len(title) < 5:
            continue

        seen.add(href)
        articles.append({"title": title, "url": href, "published_at": _nearest_date(a)})

    crawler_logger.info(f"[HuggingFace] {len(articles)} articles")
    return articles[:10]


def parse_deepmind(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    articles: list[dict] = []
    seen: set[str] = set()
    skip = {"/about", "/contact", "/careers", "/team", "?", "#"}

    for sel in ["a[href*='/discover/blog/']", "a[href*='/research/']", "h2 a", "h3 a", "h4 a"]:
        for a in soup.select(sel):
            href: str = a.get("href", "")
            if href.startswith("/"):
                href = "https://deepmind.google" + href
            if not ("deepmind.google" in href or "deepmind.com" in href):
                continue
            if any(s in href for s in skip):
                continue
            if href in seen:
                continue
            title = a.get_text(strip=True)
            if len(title) < 10:
                continue
            seen.add(href)
            articles.append({"title": title, "url": href, "published_at": _nearest_date(a)})

    crawler_logger.info(f"[DeepMind] {len(articles)} articles")
    return articles[:10]


# Registry used by the collector
SOURCE_PARSERS: dict = {
    "OpenAI Blog":          parse_openai,
    "Anthropic Blog":       parse_anthropic,
    "Hugging Face Blog":    parse_huggingface,
    "Google DeepMind Blog": parse_deepmind,
}