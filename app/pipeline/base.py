import datetime
from dataclasses import dataclass, field
from typing import Optional, Protocol, runtime_checkable

from app.utils.logger import MyLogger


@dataclass
class PipelineContext:
    messages: list[dict]
    client_ip: str
    query: str = ""
    retrieved_docs: list[str] = field(default_factory=list)
    system_prompt: str = ""
    response: str = ""


@runtime_checkable
class PipelineStep(Protocol):
    async def execute(self, ctx: PipelineContext) -> PipelineContext: ...


class RAGPipeline:
    def __init__(self, steps: list[PipelineStep], logger: Optional[MyLogger] = None) -> None:
        self._steps = steps
        self._logger = logger

    async def run(self, ctx: PipelineContext) -> str:
        for step in self._steps:
            start = datetime.datetime.now()
            ctx = await step.execute(ctx)
            if self._logger:
                self._logger.log_execution_time(type(step).__name__, start)
        return ctx.response
