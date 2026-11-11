"""
CORE — rate_limit.py

Redis-backed fixed-window rate limiter with fail-open semantics and standard headers.
"""

from collections.abc import Callable
import logging
import time
from typing import Literal
from uuid import UUID

from fastapi import HTTPException, Request, Response, status

from app.core.redis import RedisClient
from app.core.request_context import get_client_ip
from app.core.security import decode_access_token

logger = logging.getLogger(__name__)


def rate_limit(
    name: str,
    limit: int | Callable,
    window_seconds: int = 60,
    key: Literal["ip", "user", "org"] = "ip",
):
    """
    FastAPI dependency factory enforcing fixed-window rate limits via Redis.

    Parameters:
      name: Identifier for the rate-limited action (e.g. 'login', 'upload')
      limit: Max requests per window, or callable returning the limit
      window_seconds: Window duration in seconds (e.g. 60 for /min, 3600 for /hour)
      key: Subject dimension to limit by ('ip', 'user', or 'org')
    """
    async def _rate_limiter(request: Request, response: Response) -> None:
        # 1. Determine subject
        subject = "unknown"
        if key == "ip":
            subject = get_client_ip(request)
        elif key == "user":
            auth = request.headers.get("Authorization")
            if auth and auth.lower().startswith("bearer "):
                token = auth.split(" ")[1]
                try:
                    payload = decode_access_token(token)
                    subject = str(payload.get("sub", "anonymous"))
                except Exception:
                    subject = get_client_ip(request)
            else:
                subject = get_client_ip(request)
        elif key == "org":
            org_header = request.headers.get("X-Organization-Id")
            subject = org_header if org_header else get_client_ip(request)

        # 2. Determine effective limit
        eff_limit = limit
        if callable(limit):
            eff_limit = limit(request)

        # 3. Fixed-window key & reset calculation
        now = time.time()
        window_index = int(now // window_seconds)
        rl_key = f"rl:{name}:{subject}:{window_index}"
        window_reset_ts = int((window_index + 1) * window_seconds)
        retry_after = max(1, window_reset_ts - int(now))

        # 4. Redis pipeline check (atomic INCR + EXPIRE in ONE round trip)
        try:
            client = await RedisClient.get_client()
            pipe = client.pipeline()
            pipe.incr(rl_key)
            pipe.expire(rl_key, window_seconds + 5)
            results = await pipe.execute()
            current_count = int(results[0])
        except Exception as exc:
            # Fail-open: allow request on Redis connection failure or timeouts
            logger.warning("Redis rate limiter unavailable for key '%s' (failing open): %s", rl_key, exc)
            return

        # 5. Enforcement
        if current_count > eff_limit:
            headers = {
                "Retry-After": str(retry_after),
                "X-RateLimit-Limit": str(eff_limit),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(window_reset_ts),
            }
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={"code": "RATE_LIMITED", "retry_after": retry_after},
                headers=headers,
            )

        # 6. Success headers
        remaining = max(0, eff_limit - current_count)
        response.headers["X-RateLimit-Limit"] = str(eff_limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(window_reset_ts)

    return _rate_limiter

