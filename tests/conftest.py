import pytest

from app.config import Secrets
from app.dependencies import get_document_store, get_logger
from app.services.document_store import TogetherEmbeddingFunction

TEST_SECRETS = Secrets(
    TOGETHER_API_KEY="test-key",
    JWT_SECRET="test-jwt-secret",
    ADMIN_PASSWORD="test-password",
)


def _fake_embed(self, input):
    return [[0.1] * 1024 for _ in input]


@pytest.fixture(autouse=True)
def clear_lru_caches():
    get_document_store.cache_clear()
    get_logger.cache_clear()
    yield
    get_document_store.cache_clear()
    get_logger.cache_clear()
