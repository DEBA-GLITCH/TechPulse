# Ordered source definitions — single source of truth
SOURCE_METADATA: dict[str, dict] = {
    "OpenAI Blog": {
        "url":   "https://openai.com/news/",
        "color": "#10a37f",
        "dim":   "#0a3d2e",
        "short": "OpenAI",
        "icon":  "◈",
    },
    "Anthropic Blog": {
        "url":   "https://www.anthropic.com/news",
        "color": "#d4875c",
        "dim":   "#3d200f",
        "short": "Anthropic",
        "icon":  "◆",
    },
    "Hugging Face Blog": {
        "url":   "https://huggingface.co/blog",
        "color": "#ffb526",
        "dim":   "#3d2d00",
        "short": "HF Blog",
        "icon":  "◉",
    },
    "Google DeepMind Blog": {
        "url":   "https://deepmind.google/discover/blog/",
        "color": "#4d8bf9",
        "dim":   "#0d1f3c",
        "short": "DeepMind",
        "icon":  "◇",
    },
}

REQUEST_HEADERS: dict[str, str] = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection":      "keep-alive",
}