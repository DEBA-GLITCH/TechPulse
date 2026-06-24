"""
Extracts clean, readable text from an article HTML page.
"""
import re
from typing import Optional
from bs4 import BeautifulSoup
from app.core.logger import crawler_logger

_NOISE = ["nav", "footer", "header", "aside", "script", "style", "noscript", "iframe", "form", "dialog"]
_CONTENT_SELECTORS = [
    "article",
    "main article",
    "[class*='post-content']",
    "[class*='article-content']",
    "[class*='blog-content']",
    "[class*='entry-content']",
    "[class*='prose']",
    ".content",
    "main",
]


def _clean(text: str) -> str:
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def extract_content(html: str, url: str = "") -> str:
    """Return cleaned body text (max 4 000 chars) from article HTML."""
    try:
        soup = BeautifulSoup(html, "lxml")
        for tag in soup.find_all(_NOISE):
            tag.decompose()

        for sel in _CONTENT_SELECTORS:
            el = soup.select_one(sel)
            if el:
                text = _clean(el.get_text(separator="\n", strip=True))
                if len(text) > 200:
                    crawler_logger.debug(f"Extracted {len(text)}c via '{sel}' | {url[:60]}")
                    return text[:4_000]

        body = soup.find("body")
        if body:
            return _clean(body.get_text(separator="\n", strip=True))[:4_000]

        return ""
    except Exception as exc:
        crawler_logger.warning(f"Content extraction failed [{url[:60]}]: {exc}")
        return ""


def extract_og_title(html: str) -> Optional[str]:
    """Return Open Graph / <title> string, preferring OG."""
    try:
        soup = BeautifulSoup(html, "lxml")
        og = soup.find("meta", property="og:title")
        if og:
            val = og.get("content", "").strip()
            if val:
                return val
        tag = soup.find("title")
        if tag:
            return tag.get_text(strip=True)
    except Exception:
        pass
    return None