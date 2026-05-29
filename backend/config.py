from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openai_api_key: str = ""
    embed_model: str = "text-embedding-3-small"
    llm_model: str = "gpt-4o-mini"

    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_key: str = ""

    cors_origins: str = "http://localhost:5173"

    retrieval_top_k: int = 5
    rrf_k: int = 60

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]


@lru_cache
def get_settings() -> Settings:
    return Settings()
