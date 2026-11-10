from functools import lru_cache
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Telegram
    BOT_TOKEN: str

    # LLM
    LLM_PROVIDER: str = "openai"  # openai | xai | anthropic | deepseek
    LLM_API_KEY: str
    LLM_MODEL: str = "gpt-4o"
    LLM_BASE_URL: Optional[str] = None
    LLM_TEMPERATURE: float = 0.2
    LLM_MAX_TOKENS: int = 16000

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/bot_generator.db"

    # Redis (FSM + rate limit, optional)
    REDIS_URL: str = "redis://localhost:6379/0"
    USE_REDIS: bool = False

    # Webhook mode
    USE_WEBHOOK: bool = False
    WEBHOOK_HOST: str = "https://your-domain.com"  # public HTTPS URL
    WEBHOOK_PATH: str = "/webhook"
    WEBHOOK_SECRET: str = "change-me-secret"
    WEBAPP_HOST: str = "0.0.0.0"
    WEBAPP_PORT: int = 8080

    # GitHub
    GITHUB_TOKEN: Optional[str] = None
    GITHUB_USERNAME: Optional[str] = None

    # Admins
    ADMIN_IDS: str = ""

    # Limits
    MAX_BOTS_PER_DAY: int = 10
    MAX_GENERATION_TOKENS: int = 16000

    # App
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    ENVIRONMENT: str = "production"

    @property
    def admin_ids_list(self) -> List[int]:
        if not self.ADMIN_IDS.strip():
            return []
        return [int(x.strip()) for x in self.ADMIN_IDS.split(",") if x.strip()]

    @property
    def is_openai_compatible(self) -> bool:
        return self.LLM_PROVIDER.lower() in {"openai", "xai", "deepseek"}

    @property
    def webhook_url(self) -> str:
        return f"{self.WEBHOOK_HOST.rstrip('/')}{self.WEBHOOK_PATH}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
