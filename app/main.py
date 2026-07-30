"""
Application entry point.

Request flow (simplified):
  HTTP Request
    -> CORSMiddleware (browser cross-origin; optional until you have a frontend)
    -> TenantContextMiddleware (stores X-Organization-Id in context; optional helper)
    -> Router (auth / organizations / invitations / files)
         -> Depends: get_db, get_current_user, get_current_membership, ...
         -> Service (business rules)
         -> Repository (SQL)
    -> JSON response

Run: uvicorn app.main:app --reload
Docs: http://127.0.0.1:8000/docs
"""

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.redis import RedisClient
from app.middleware.tenant import TenantContextMiddleware
from app.modules.audit.router import router as audit_router
from app.modules.auth.router import router as auth_router
from app.modules.files.router import router as files_router
from app.modules.invitations.router import router as invitations_router
from app.modules.memberships.router import router as memberships_router
from app.modules.organizations.router import router as organizations_router

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Startup/shutdown hooks for Redis and other resources."""
    # Startup: Connect to Redis
    try:
        await RedisClient.get_client()
    except Exception as e:
        # Fail fast if Redis is unavailable
        raise RuntimeError(f"Failed to connect to Redis: {e}")
    
    yield
    
    # Shutdown: Close Redis connection
    await RedisClient.close()


app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    lifespan=lifespan,
)

# Allows a separate frontend origin (e.g. localhost:3000) to call this API from the browser
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Optional: copies X-Organization-Id into a ContextVar (see middleware/tenant.py)
app.add_middleware(TenantContextMiddleware)

# Each module exposes an APIRouter; paths are defined inside each router.py
app.include_router(auth_router)
app.include_router(organizations_router)
app.include_router(invitations_router)
app.include_router(files_router)
app.include_router(memberships_router)
app.include_router(audit_router)


@app.get("/health")
async def health() -> dict[str, str]:
    """Liveness check with database and Redis status."""
    redis_status = "connected" if await RedisClient.health_check() else "disconnected"
    
    # Check database connection
    from sqlalchemy import text

    from app.core.database import engine

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception:
        db_status = "disconnected"
    
    return {
        "status": "ok",
        "database": db_status,
        "redis": redis_status,
    }
