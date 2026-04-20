from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class Secrets(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    TOGETHER_API_KEY: str
    JWT_SECRET: str
    ADMIN_PASSWORD: str
    HISTORY_KEY: str


class AppConfig(BaseModel):
    chat_model: str
    embedding_model: str
    retrieve_top_k: int
    max_chars: int
    chat_rate_limit: int
    port: int
    log_file: str
    chroma_db_path: str
    documents_path: str
    conversations_db_path: str
    environment: str


def load_config(path: str = "configs/config.yaml") -> AppConfig:
    return AppConfig(**yaml.safe_load(Path(path).read_text()))


_secrets: Optional[Secrets] = None
_config: Optional[AppConfig] = None


def get_secrets() -> Secrets:
    global _secrets
    if _secrets is None:
        _secrets = Secrets()
    return _secrets


def get_config() -> AppConfig:
    global _config
    if _config is None:
        _config = load_config()
    return _config
