import logging
import time
from pathlib import Path

from fastapi import HTTPException, Request

rate_limit_store: dict[tuple[str | None, str], list[float]] = {}


def requires_env() -> None:
    if not Path(".env").exists():
        raise HTTPException(
            status_code=400, detail="Environment configuration missing."
        )


def get_giacomino(request: Request):
    return request.app.state.giacomino


def rate_limit(request_count: int, h: int):
    def dependency(request: Request) -> None:
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            user = forwarded_for.split(",")[0].strip()
        else:
            user = request.client.host if request.client else None
        endpoint = request.url.path
        key = (user, endpoint)
        now = time.time()
        window = h * 3600

        timestamps = rate_limit_store.get(key, [])
        timestamps = [ts for ts in timestamps if now - ts < window]

        if len(timestamps) >= request_count:
            raise HTTPException(
                status_code=429, detail="Rate limit exceeded. Please try again later."
            )

        logging.getLogger("giacomino").info(
            f"[RateLimit] Allowed: user={user}, endpoint={endpoint}, "
            f"count={len(timestamps)}/{request_count} in last {h}h"
        )

        timestamps.append(now)
        rate_limit_store[key] = timestamps

    return dependency
