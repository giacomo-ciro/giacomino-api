import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import aiosqlite
from pydantic_ai import Agent
from pydantic_ai.messages import ModelRequest, SystemPromptPart, UserPromptPart
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from app.config import AppConfig, Secrets
from app.pipeline.base import PipelineContext
from app.services.document_store import DocumentStore
from app.utils.logger import MyLogger


class EmbedQueryStep:
    def __init__(self, logger: Optional[MyLogger] = None) -> None:
        self._logger = logger

    async def execute(self, ctx: PipelineContext) -> PipelineContext:
        ctx.query = ctx.messages[-1]["content"]
        if self._logger:
            self._logger.debug(f"EmbedQueryStep: query='{ctx.query[:80]}'")
        return ctx


class RetrieveDocsStep:
    def __init__(self, store: DocumentStore, config: AppConfig, logger: Optional[MyLogger] = None) -> None:
        self._store = store
        self._top_k = config.retrieve_top_k
        self._logger = logger

    async def execute(self, ctx: PipelineContext) -> PipelineContext:
        ctx.retrieved_docs = self._store.query(ctx.query, self._top_k)
        if self._logger:
            self._logger.debug(f"RetrieveDocsStep: retrieved {len(ctx.retrieved_docs)} docs")
        return ctx


class BuildPromptStep:
    def __init__(self, system_template: str, logger: Optional[MyLogger] = None) -> None:
        self._template = system_template
        self._logger = logger

    async def execute(self, ctx: PipelineContext) -> PipelineContext:
        context = "\n".join(ctx.retrieved_docs) if ctx.retrieved_docs else "No specific context available."
        ctx.system_prompt = self._template.format(
            context=context,
            date=time.strftime("%-d %B %Y"),
        )
        if self._logger:
            self._logger.debug(f"BuildPromptStep: system prompt {len(ctx.system_prompt)} chars")
        return ctx


class GenerateResponseStep:
    def __init__(self, secrets: Secrets, config: AppConfig, logger: Optional[MyLogger] = None) -> None:
        model = OpenAIChatModel(
            config.chat_model,
            provider=OpenAIProvider(
                base_url="https://api.together.xyz/v1",
                api_key=secrets.TOGETHER_API_KEY,
            ),
        )
        self._agent = Agent(model=model)
        self._logger = logger

    async def execute(self, ctx: PipelineContext) -> PipelineContext:
        # Build message history: system prompt first, then prior turns
        history: list = [ModelRequest(parts=[SystemPromptPart(content=ctx.system_prompt)])]
        prior_messages = ctx.messages[:-1]
        for msg in prior_messages:
            if msg["role"] == "user":
                history.append(ModelRequest(parts=[UserPromptPart(content=msg["content"])]))

        result = await self._agent.run(ctx.query, message_history=history)
        ctx.response = str(result.output)
        if self._logger:
            self._logger.debug(f"GenerateResponseStep: response {len(ctx.response)} chars")
        return ctx


class PersistHistoryStep:
    _CREATE_TABLE = """
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            client_ip TEXT NOT NULL,
            user_message TEXT NOT NULL,
            assistant_response TEXT NOT NULL,
            metadata TEXT DEFAULT '{}'
        )
    """

    def __init__(self, db_path: str, logger: Optional[MyLogger] = None) -> None:
        self._db_path = db_path
        self._logger = logger

    async def setup(self) -> None:
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(self._CREATE_TABLE)
            await db.commit()

    async def execute(self, ctx: PipelineContext) -> PipelineContext:
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                "INSERT INTO conversations (timestamp, client_ip, user_message, assistant_response) VALUES (?, ?, ?, ?)",
                (datetime.now().isoformat(), ctx.client_ip, ctx.query, ctx.response),
            )
            await db.commit()
        if self._logger:
            self._logger.debug(f"PersistHistoryStep: persisted conversation for {ctx.client_ip}")
        return ctx
