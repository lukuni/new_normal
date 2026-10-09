"""Application settings, read from environment variables."""
import os


class Settings:
    # PostgreSQL in production, e.g. postgresql+psycopg2://zaluu:zaluu@db:5432/zaluu
    # Falls back to a local SQLite file so the backend runs with zero setup.
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./zaluu.db")

    # Token required in the X-Admin-Token header for admin endpoints.
    admin_token: str = os.getenv("ADMIN_TOKEN", "change-me")

    # Optional LLM classifier. When ANTHROPIC_API_KEY is empty, the rule-based
    # Mongolian classifier is used.
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    llm_model: str = os.getenv("LLM_MODEL", "claude-haiku-5-5")
    llm_timeout_s: float = float(os.getenv("LLM_TIMEOUT_S", "15"))

    # Demo mode enables the tamper/restore endpoints used in live presentations.
    demo_mode: bool = os.getenv("DEMO_MODE", "false").lower() == "true"

    cors_origins: list[str] = [o.strip() for o in os.getenv(
        "CORS_ORIGINS", "http://localhost:5173,http://localhost:8080").split(",") if o.strip()]

    # Seed demo data on first start when the database is empty.
    seed_on_start: bool = os.getenv("SEED_ON_START", "true").lower() == "true"


settings = Settings()
