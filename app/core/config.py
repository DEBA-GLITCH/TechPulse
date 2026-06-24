from pathlib import Path
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_FILES = [
    BASE_DIR / ".env",
    BASE_DIR / "app" / ".env",
]
for env_file in ENV_FILES:
    load_dotenv(env_file, override=False)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=[str(path) for path in ENV_FILES],
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    APP_NAME: str = "TechPulse"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # LLM
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.1-8b-instant"

    # Database
    DATABASE_URL: str = "sqlite:///./data/techpulse.db"

    # Crawler
    CRAWL_INTERVAL_HOURS: int = 6
    REQUEST_TIMEOUT: int = 30
    MAX_ARTICLES_PER_SOURCE: int = 10

    # Paths (computed)
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent

    @property
    def LOGS_DIR(self) -> Path:
        return self.BASE_DIR / "logs"

    @property
    def DATA_DIR(self) -> Path:
        return self.BASE_DIR / "data"

    def bootstrap(self):
        """Create required directories on startup."""
        self.LOGS_DIR.mkdir(parents=True, exist_ok=True)
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
        (self.BASE_DIR / "app" / "static").mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.bootstrap()