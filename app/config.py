from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    TOGETHER_API_KEY: str
    RETRIEVE_TOP_K: int = 10
    MAX_CHARS: int = 2048
    LOG_FILE: str | None = None
    TEXT_MODEL_PATH: str = "meta-llama/Llama-3.2-3B-Instruct-Turbo"
    EMB_MODEL_PATH: str = "BAAI/bge-large-en-v1.5"
    CHAT_REQUESTS_PER_HOUR_LIMIT: int
    CHROMA_PERSIST_DIR: str = "chroma_data"


@lru_cache
def get_settings() -> Settings:
    return Settings()
