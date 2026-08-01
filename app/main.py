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
from app.modules.jobs.router import router as jobs_router
from app.modules.memberships.router import router as memberships_router
from app.modules.organizations.router import router as organizations_router
from app.modules.search.router import router as search_router

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Startup/shutdown hooks for Redis and other resources."""
    # Startup: Connect to Redis
    try:
        await RedisClient.get_client()
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("Failed to connect to Redis during startup: %s. Continuing...", str(e))

    
    # Startup: Connect and initialize Meilisearch
    from app.infrastructure.search.client import search_client
    from app.infrastructure.search.index_manager import IndexManager
    try:
        connected = await search_client.initialize()
        if connected:
            await IndexManager.initialize_indexes()
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("Failed to initialize Meilisearch on startup: %s. Continuing...", str(e))

    yield
    
    # Shutdown: Close Redis connection
    await RedisClient.close()
    
    # Shutdown: Close Meilisearch connection
    try:
        from app.infrastructure.search.client import search_client
        await search_client.close()
    except Exception:
        pass


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
app.include_router(jobs_router)
app.include_router(search_router)




@app.get("/health")
async def health() -> dict:
    """Liveness check with database, Redis, worker, search, and queue status."""
    from app.services.job_service import JobService
    from app.infrastructure.search.health import check_search_health

    redis_status = "connected" if await RedisClient.health_check() else "disconnected"
    
    # Check database connection
    from sqlalchemy import text

    from app.core.database import engine

    try:
        async def _check_db():
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
        import asyncio
        await asyncio.wait_for(_check_db(), timeout=1.0)
        db_status = "connected"
    except Exception:
        db_status = "disconnected"

    # Check Meilisearch health status
    search_status = await check_search_health()

    worker_stats = {"count": 0, "status": "unknown", "workers": []}
    queue_stats: dict = {}
    if redis_status == "connected":
        try:
            worker_stats = JobService.get_worker_stats()
            queue_stats = JobService.get_queue_stats()
        except Exception:
            worker_stats = {"count": 0, "status": "unknown", "workers": []}
    
    is_ok = (
        db_status == "connected" 
        and redis_status == "connected" 
        and search_status == "connected"
    )
    status_str = "ok" if is_ok else "degraded"
    
    return {
        "status": status_str,
        "database": db_status,
        "redis": redis_status,
        "search": search_status,
        "worker": worker_stats["status"],
        "workers": worker_stats,
        "queues": queue_stats,
    }

