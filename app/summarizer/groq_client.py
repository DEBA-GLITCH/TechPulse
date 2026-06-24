"""
Groq LLM wrapper for article summarization.
Runs synchronous Groq SDK in a thread executor to stay non-blocking.
"""
import asyncio
import json
import re
from functools import partial
from typing import Any

from groq import Groq

from app.core.config import settings
from app.core.logger import app_logger, error_logger

_client: Groq | None = None


def _groq() -> Groq:
    global _client
    if _client is None:
        _client = Groq(api_key=settings.GROQ_API_KEY)
    return _client


_SYSTEM = """\
You are a senior AI research analyst who distills technical articles for busy engineers.
Always respond with valid JSON only — no markdown fences, no prose outside the JSON.
"""

_PROMPT = """\
Analyze the article below and return a JSON object with exactly these keys:

"short_summary"  : 2-3 sentence summary — what it is, why it matters
"key_takeaways"  : array of 3-5 concise strings (active voice, specific)
"importance_score": integer 1-10

Scoring rubric:
  9-10 → Major model release / paradigm-shift / safety breakthrough
  7-8  → Significant capability gain / important research result
  5-6  → Useful tool or feature / interesting finding
  3-4  → Minor update / incremental improvement
  1-2  → Announcement / event / housekeeping post

Source : {source}
Title  : {title}

Content:
{content}

Return JSON only:"""


def _call(title: str, content: str, source: str) -> dict[str, Any]:
    prompt = _PROMPT.format(source=source, title=title, content=content[:3_000])
    resp = _groq().chat.completions.create(
        model=settings.GROQ_MODEL,
        messages=[
            {"role": "system", "content": _SYSTEM},
            {"role": "user",   "content": prompt},
        ],
        max_tokens=800,
        temperature=0.25,
    )
    raw = resp.choices[0].message.content.strip()
    # Strip accidental markdown fences
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, re.S)
        if match:
            return json.loads(match.group(0))
        raise


_FALLBACK: dict[str, Any] = {
    "short_summary":   None,
    "key_takeaways":   [],
    "importance_score": 5,
}


async def summarize_article(title: str, content: str, source: str = "") -> dict[str, Any]:
    if not settings.GROQ_API_KEY:
        error_logger.error("GROQ_API_KEY not configured — summarization skipped")
        return _FALLBACK.copy()

    try:
        loop   = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, partial(_call, title, content, source))

        validated = {
            "short_summary":    (str(result.get("short_summary") or ""))[:1_200] or None,
            "key_takeaways":    [str(t) for t in (result.get("key_takeaways") or [])[:6]],
            "importance_score": max(1, min(10, int(result.get("importance_score") or 5))),
        }
        app_logger.info(
            f"[Groq] '{title[:45]}' → score={validated['importance_score']}"
        )
        return validated

    except json.JSONDecodeError as exc:
        error_logger.error(f"[Groq] JSON parse error for '{title[:40]}': {exc}")
    except Exception as exc:
        error_logger.error(f"[Groq] API failure for '{title[:40]}': {exc}")

    return _FALLBACK.copy()