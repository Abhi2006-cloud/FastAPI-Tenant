# AI Workspace SaaS

A production-ready multi-tenant SaaS application with FastAPI backend and Streamlit frontend.

## Overview

AI Workspace is a modular monolith SaaS application featuring:
- **Multi-tenant architecture** with organization-based isolation
- **JWT authentication** with role-based access control
- **File management** with tenant-scoped storage
- **Invitation system** for team collaboration
- **Clean architecture** with separated layers (router, service, repository, models, schemas)
- **Streamlit frontend** for complete user interface

## Tech Stack

### Backend
- **FastAPI** - Modern, fast web framework for building APIs
- **SQLAlchemy 2.0** - Async ORM with declarative models
- **PostgreSQL** - Relational database (supports local and Neon)
- **Redis** - In-memory data store for caching and infrastructure
- **Alembic** - Database migration tool
- **Pydantic** - Data validation using Python type annotations
- **JWT** - Token-based authentication

### Frontend
- **Streamlit** - Python framework for data apps
- **Requests** - HTTP client for API communication
- **Pandas** - Data manipulation and display

## Architecture

The application follows **clean architecture** with strict separation of concerns per module:

| Layer        | Responsibility                          |
|-------------|------------------------------------------|
| `router.py` | HTTP request/response handling only      |
| `service.py`| Business logic and authorization         |
| `repository.py` | Database access                    |
| `models.py` | SQLAlchemy ORM models                    |
| `schemas.py`| Pydantic validation / API contracts      |

**Multi-tenancy** is enforced at the service and dependency layers:

- JWT identifies the authenticated user
- `X-Organization-Id` header selects the active tenant (organization)
- Membership is verified before any organization-scoped operation
- Queries are scoped by `organization_id`

## Redis & Caching Architecture

### Overview

Redis is introduced as a first-class infrastructure component for caching and future features (rate limiting, background jobs, sessions, distributed locks). The application uses a centralized caching layer following the **Cache-Aside pattern**.

### Infrastructure Layers

```
Routers
  ↓
Services
  ↓
CacheService (Cache-Aside pattern)
  ↓
RedisService (low-level Redis operations)
  ↓
Redis
```

### Cache-Aside Pattern

The `CacheService` implements the Cache-Aside pattern:

1. **Cache Hit**: Return cached data immediately
2. **Cache Miss**: Query database, store in cache, return data
3. **Cache Invalidation**: Explicitly invalidate cache when data changes

```python
# Example usage in services
async def list_user_organizations(self, user_id: UUID) -> list[Organization]:
    cache_key = CacheKeyBuilder.user(str(user_id))
    
    async def fetch_from_db():
        orgs = await self.repo.list_for_user(user_id)
        return [OrganizationResponse.model_validate(org).model_dump() for org in orgs]
    
    cached_data = await self.cache.get_or_set(
        cache_key,
        fetch_from_db,
        ttl=CacheTTL.MEDIUM,
    )
    
    return [Organization(**org_data) for org_data in cached_data]
```

### Cache Key Naming Convention

Cache keys use a centralized `CacheKeyBuilder` with namespaces:

| Namespace    | Pattern                  | Example                     |
|--------------|--------------------------|-----------------------------|
| user         | `user:{user_id}`         | `user:123e4567-e89b-12d3`   |
| organization | `organization:{org_id}`  | `organization:456e789a-12d3`|
| membership   | `membership:{user_id}:{org_id}` | `membership:123:456` |
| invitation   | `invitation:{invite_id}` | `invitation:789abc-def`     |
| file         | `file:{file_id}`         | `file:abc123-def456`        |
| audit        | `audit:{org_id}`         | `audit:456e789a-12d3`       |

### TTL Strategy

Centralized TTL constants in `CacheTTL`:

| TTL Constant | Duration | Use Case                          |
|--------------|----------|-----------------------------------|
| SHORT        | 5 min    | Frequently changing data           |
| MEDIUM       | 15 min   | User sessions, organization lists |
| LONG         | 1 hour   | Member lists, file metadata       |
| VERY_LONG    | 24 hours | Static configuration              |
| DEFAULT      | 15 min   | Default TTL                       |

### Cache Invalidation

Cache is invalidated on data mutations:

- **Organization created**: Invalidate user's organization list
- **Membership accepted**: Invalidate user's organization list
- **Role changed**: Invalidate target user's organization list
- **Member removed**: Invalidate removed user's organization list
- **Ownership transferred**: Invalidate both users' organization lists

### Health Check

The `/health` endpoint includes Redis, worker, and queue status:

```json
{
  "status": "ok",
  "database": "connected",
  "redis": "connected",
  "worker": "running",
  "workers": {
    "count": 1,
    "status": "running",
    "workers": [{"name": "...", "state": "busy", "queues": ["default", "high", "low"]}]
  },
  "queues": {
    "default": {"queued": 0, "started": 0, "finished": 12, "failed": 0},
    "high": {"queued": 0, "started": 0, "finished": 0, "failed": 0},
    "low": {"queued": 0, "started": 0, "finished": 0, "failed": 0}
  }
}
```

### Future-Ready Design

The Redis infrastructure supports future features:

- **Rate Limiting**: Use `RedisService.increment()` with TTL
- **Session Storage**: Use `RedisService.json_set()` for session data
- **Background Jobs**: Centralized RQ task processing (see details below)

## Background Job Architecture (v2.1.0)

### Overview

Background job processing is powered by **RQ (Redis Queue)** and managed through a centralized `JobService` interface (`app/services/job_service.py`). Background tasks delegate to the service layer via async database sessions, using clean event loop connection pool disposal for zero connection leaks.

### Architecture Flow

```
FastAPI Service Layer
  ↓ (enqueue / enqueue_high_priority / enqueue_low_priority / enqueue_delayed)
JobService
  ↓
RQ Queues (default, high, low)
  ↓
Redis (Raw binary storage: decode_responses=False)
  ↓
RQ Worker Process (python -m app.jobs.worker)
  ↓
async_runner (_execute_with_cleanup -> engine.dispose())
  ↓
Database / Storage / Audit Log Persistence
```

### Key Components

- **`JobService` (`app/services/job_service.py`)**: Single interface for background job management (enqueueing, listing, status lookup, retry, cancellation). Routers and services interact exclusively with `JobService`.
- **`Worker` (`app/jobs/worker.py`)**: RQ worker process listening to `default`, `high`, and `low` priority queues with graceful shutdown signal handling (`SIGTERM`/`SIGINT`).
- **`async_runner` (`app/jobs/async_runner.py`)**: Executes async coroutines within worker processes. Wraps tasks in a cleanup coroutine that disposes of the SQLAlchemy engine pool (`await engine.dispose()`) inside a `finally` block before `asyncio.run()` closes the event loop.
- **`scheduler` (`app/jobs/scheduler.py`)**: Enqueues delayed tasks via `enqueue_in()`, respecting `JOB_SYNC_MODE`.
- **Binary Redis Connection (`app/core/rq.py`)**: Connects to Redis with `decode_responses=False` so RQ can store and retrieve raw binary pickled job payloads cleanly.
- **`JOB_SYNC_MODE`**: When `JOB_SYNC_MODE=true` (default in tests), tasks execute synchronously on the active thread for deterministic testing and local development without Redis.

### Running RQ Workers

Start an RQ worker process in your terminal:

```bash
python -m app.jobs.worker
```

### Job Management APIs

- `GET /jobs`: List background jobs (supports optional query params: `status`, `queue`, `limit`).
- `GET /jobs/{job_id}`: Retrieve detailed job status, execution timestamps, serializable result, or error trace payload.

- **Distributed Locks**: Use `RedisService.set()` with NX flag
- **Real-time Features**: Use Redis pub/sub (future implementation)

## Background Jobs Architecture (v2.1.0)

### Overview

Asynchronous task processing uses **RQ (Redis Queue)** with the existing Redis connection. Jobs are enqueued through `JobService` — routers and services never talk to RQ directly.

```
Request → Router → Service → JobService → RQ Queue → Redis → Worker → Task → Service Layer
```

### Project Structure

```
app/
├── core/rq.py              # Shared sync Redis connection for RQ
├── jobs/
│   ├── queue.py            # Queue names (default, high, low)
│   ├── tasks.py            # Worker task functions
│   ├── worker.py           # Worker process entry point
│   ├── scheduler.py        # Delayed job scheduling
│   └── job_status.py       # Status mapping helpers
├── services/job_service.py # Single interface for enqueue/status/cancel/retry
└── modules/jobs/router.py  # GET /jobs, GET /jobs/{job_id}
```

### Queues

| Queue   | Purpose                          |
|---------|----------------------------------|
| default | Standard background jobs         |
| high    | Time-sensitive tasks             |
| low     | Batch / non-urgent work          |

### Background Tasks

| Task | Trigger | Worker Action |
|------|---------|---------------|
| `record_audit_event_task` | Any `AuditLogService.create_event()` call | Persists audit log to database |
| `process_file_upload_task` | File upload completes | Collects file metadata (extensible for virus scan, thumbnails) |
| `process_invitation_task` | Invitation created | Processes invitation event (extensible for email delivery) |

### Retry Strategy

Configurable via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `RQ_RETRY_MAX` | 3 | Maximum retry attempts |
| `RQ_RETRY_INTERVALS` | `10,30,60` | Seconds between retries |
| `RQ_JOB_TIMEOUT` | 300 | Job timeout in seconds |

Failed jobs are logged with exception info. Workers do not crash on task failure.

### Job Status API

| Method | Path | Description |
|--------|------|-------------|
| GET | `/jobs/{job_id}` | Job status (queued, started, finished, failed) |
| GET | `/jobs` | List jobs (filter by status, queue) |

### Running Workers

Three processes run together in development:

```bash
# Terminal 1 — API
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2 — RQ Worker
python -m app.jobs.worker

# Terminal 3 — Streamlit Admin
cd frontend && streamlit run app.py
```

The API enqueues jobs to Redis. The worker pulls jobs from Redis and executes task functions. Streamlit monitors job status via the `/jobs` API.

### Development / Testing

Set `JOB_SYNC_MODE=true` to execute jobs synchronously without a worker (used automatically in pytest).

```bash
JOB_SYNC_MODE=true uvicorn app.main:app --reload
```

## Search Infrastructure (v2.2.0)

### Overview

Full-text search in the SaaS platform is powered by **Meilisearch Cloud**. Search is designed as an **optional infrastructure component** that degrades gracefully:
- If Meilisearch is unreachable, has expired credentials, or is offline, all other core SaaS features continue running normally.
- Search-related APIs return a clear `503 Service Unavailable` error instead of internal stack traces.
- Streamlit displays a warning banner and disables only search components while keeping the rest of the dashboard responsive.

### Architecture

All search requests flow through a dedicated infrastructure layer. Direct communication with Meilisearch from routers is prohibited.

```
FastAPI Router → SearchService → CacheService (Cache-Aside)
                                   ↓
                             SearchRepository
                                   ↓ (Circuit Breaker)
                             SearchClient → Meilisearch Cloud API
```

### Environment Variables

Add the following to your `.env` file (configured in `app/core/config.py`):

```ini
# Meilisearch Cloud
MEILISEARCH_URL=https://ms-xxx.meilisearch.io
MEILISEARCH_API_KEY=your-admin-api-key
MEILISEARCH_INDEX_PREFIX=ai_workspace
```

### Circuit Breaker Behavior

To prevent blocking application workers and routers during search service outages, a lightweight in-memory Circuit Breaker is active on the `SearchClient`:
- **State CLOSED**: Requests hit Meilisearch. If 5 consecutive requests fail (connection errors, timeouts, 5xx), the breaker enters **OPEN**.
- **State OPEN**: Requests are blocked immediately. The client raises a `MeilisearchUnavailableException` without hitting the network.
- **State HALF-OPEN**: After a **30-second cooldown**, the next single request acts as a trial. A success transitions the breaker to **CLOSED**; a failure returns it to **OPEN**.

### Index Configuration & Lifecycle

Indexes are automatically created and updated with appropriate settings on application startup (within FastAPI `lifespan` hooks).

| Base Index Name | Full Index Name | Filterable Attributes | Sortable Attributes |
|-----------------|-----------------|-----------------------|---------------------|
| `organizations` | `ai_workspace_organizations` | `id` | `created_at` |
| `members`       | `ai_workspace_members`       | `organization_id`, `id`, `user_id` | `created_at` |
| `files`         | `ai_workspace_files`         | `organization_id`, `id` | `created_at` |
| `audit_logs`    | `ai_workspace_audit_logs`    | `organization_id`, `id`, `action` | `created_at` |

- **Multi-Tenancy isolation**: Every query includes an organization filter (e.g. `organization_id = '{organization_id}'`). Results are strictly filtered to the active tenant.
- **Document Mapping**: Database ORM models are converted to indexable payloads via `app/infrastructure/search/document_mapper.py` before transfer.

### Background Indexing

To keep API responses fast, Meilisearch index updates are processed asynchronously by RQ workers.

| Operation Trigger | Job Function | Action in Meilisearch |
|-------------------|--------------|-----------------------|
| Organization created | `index_organization_task` | Index new organization & owner membership |
| Organization renamed | `index_organization_task` | Re-index organization name |
| Member added | `index_member_task` | Index member document (Membership + User) |
| Member role changed | `index_member_task` | Re-index modified membership role |
| Member removed | `delete_member_task` | Remove member from index |
| Ownership transferred | `index_member_task` (x2) | Re-index new owner and new admin role |
| File uploaded | `index_file_task` | Index file metadata |
| File deleted | `delete_file_task` | Remove file metadata from index |
| Audit event created | `index_audit_log_task` | Index audit log entry |

### Cache-Aside Integration

Search queries are cached inside Redis to speed up repeated queries:
- Popular queries are stored using the pattern `search:{org_id}:{index}:{query}:{limit}:{offset}:{sort}` with a short TTL (5 minutes).
- Whenever a document is indexed, updated, or deleted under an organization, all search caches matching the pattern `search:{org_id}:*` are instantly invalidated.

### Failure Handling

If a background task fails to index a document:
1. The task raises an exception, allowing the standard RQ worker retry strategy (`RQ_RETRY_MAX`, default 3) to execute.
2. If all retries are exhausted, the worker catches the failure, logs the issue, and writes detailed metadata (including the failed payload) to the `search_index_failures` database table.
3. The worker then continues executing remaining jobs in the queue normally without crashing.

### Health Check

The `/health` endpoint is extended to return search connectivity:
- Healthy: `"search": "connected"`, `"status": "ok"`
- Unhealthy: `"search": "unavailable"`, `"status": "degraded"` (returns HTTP 200)

## Project Structure

```
FastAPI-Tenant/
├── app/                    # Backend application
│   ├── core/              # Config, database, security, dependencies
│   ├── middleware/        # Tenant context middleware
│   ├── modules/
│   │   ├── auth/          # Authentication (register, login, profile)
│   │   ├── organizations/ # Organization management
│   │   ├── memberships/   # User-organization relationships
│   │   ├── invitations/   # Invitation system
│   │   ├── files/         # File upload and management
│   │   ├── audit/         # Audit logs and activity tracking
│   │   └── jobs/          # Background job status API
│   ├── jobs/              # RQ workers, queues, tasks
│   ├── services/          # Cross-cutting services (JobService)
│   ├── utils/             # Utility functions
│   ├── tests/             # Test suite
│   └── main.py            # FastAPI application entry
├── frontend/              # Streamlit frontend
│   ├── api/               # API client layer
│   ├── components/        # Reusable UI components
│   ├── pages/             # Page implementations
│   ├── utils/             # Frontend utilities
│   └── app.py             # Streamlit entry point
├── alembic/               # Database migrations
├── uploads/               # Local file storage (gitignored)
├── .env.example           # Environment template
├── requirements.txt       # Python dependencies
└── README.md              # This file
```

## Requirements

- Python 3.12+
- PostgreSQL 14+

## Setup

### 1. Clone and create virtual environment

```bash
cd FastAPI-Tenant
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Environment variables

```bash
cp .env.example .env
```

Edit `.env` and set at minimum:

- `DATABASE_URL` — async PostgreSQL URL (`postgresql+asyncpg://...`)
- `SECRET_KEY` — long random secret for JWT signing

### 3. Create database

```bash
createdb ai_workspace
```

### 4. Run migrations

Install a sync PostgreSQL driver for Alembic (if not already installed):

```bash
pip install psycopg2-binary
```

```bash
alembic upgrade head
```

### 5. Run Redis (required)

```bash
# macOS with Homebrew
brew services start redis

# Or Docker
docker run -d -p 6379:6379 redis:7
```

### 6. Run the backend API

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open interactive docs: http://localhost:8000/docs

### 7. Run the RQ worker (required for async jobs)

```bash
python -m app.jobs.worker
```

### 8. Run the frontend (optional)

```bash
cd frontend
pip install -r requirements.txt
streamlit run app.py
```

Open frontend: http://localhost:8501

## API overview

### Authentication

| Method | Path             | Description        |
|--------|------------------|--------------------|
| POST   | `/auth/register` | Register user      |
| POST   | `/auth/login`    | Login (JWT)        |
| GET    | `/auth/me`       | Current user       |

### Organizations

| Method | Path                  | Description              |
|--------|-----------------------|--------------------------|
| POST   | `/organizations`      | Create organization      |
| GET    | `/organizations/my`   | List user's organizations|

### Members

| Method | Path                                      | Description              |
|--------|-------------------------------------------|--------------------------|
| GET    | `/organizations/{org_id}/members`         | List organization members|
| PATCH  | `/organizations/{org_id}/members/{membership_id}/role` | Change member role |
| DELETE | `/organizations/{org_id}/members/{membership_id}` | Remove member |
| POST   | `/organizations/{org_id}/transfer-ownership` | Transfer ownership |

### Invitations

| Method | Path                                | Description        |
|--------|-------------------------------------|--------------------|
| POST   | `/organizations/{org_id}/invite`    | Create invite token|
| POST   | `/invitations/accept`               | Accept invitation  |

### Files (tenant-scoped)

Requires header: `X-Organization-Id: <uuid>`

| Method | Path                        | Description                    |
|--------|-----------------------------|--------------------------------|
| POST   | `/files/upload`             | Upload file                    |
| GET    | `/files`                    | List organization files         |
| GET    | `/files/stats`              | Get file statistics             |
| GET    | `/files/{file_id}`          | Get file details                |
| GET    | `/files/{file_id}/download` | Download file                   |
| DELETE | `/files/{file_id}`          | Delete file (RBAC enforced)      |

**File Deletion Permissions:**
- `owner`: Can delete any file
- `admin`: Can delete any file
- `member`: Can only delete files they uploaded

### Audit Logs (tenant-scoped)

Requires header: `X-Organization-Id: <uuid>`

| Method | Path                  | Description                              |
|--------|-----------------------|------------------------------------------|
| GET    | `/audit-logs`         | List audit events (paginated, filterable)|
| GET    | `/audit-logs/search`  | Search audit events by action, type, metadata |

**Query parameters for `/audit-logs`:**
- `page`, `page_size` — pagination (default page 1, page_size 20)
- `action` — filter by action (e.g. `FILE_UPLOADED`)
- `actor_user_id` — filter by actor UUID
- `resource_type` — filter by resource type (e.g. `file`)
- `start_date`, `end_date` — UTC datetime range filters

**Query parameters for `/audit-logs/search`:**
- `q` — search action, resource type, or metadata text
- `action`, `resource_type` — optional exact filters
- `page`, `page_size` — pagination

**Read access:** All organization members (owner, admin, member) can read audit logs for their organization.

### Health

| Method | Path      |
|--------|-----------|
| GET    | `/health` |

### Background Jobs

| Method | Path              | Description                    |
|--------|-------------------|--------------------------------|
| GET    | `/jobs/{job_id}`  | Get job status and result      |
| GET    | `/jobs`           | List jobs (filter by status)   |

## Authorization

**Roles** (`memberships` module):

- `owner` — full control, can manage members, transfer ownership
- `admin` — can invite users, view members
- `member` — standard access (files, view members)

**Member Management** (v1.3.0):

- List members: Any organization member
- Change roles: Only owner
- Remove members: Only owner
- Transfer ownership: Only current owner

Invitations require `owner` or `admin`. File upload/list require any active membership.

## Audit Architecture (v1.5.0)

Audit logging is a core infrastructure capability. Business services record events via `AuditLogService.create_event()` — they never write to the `audit_logs` table directly.

**As of v2.1.0**, audit events are enqueued as background jobs and persisted asynchronously by RQ workers.

**Design:**
- Append-only `audit_logs` table scoped by `organization_id`
- Centralized `AuditAction` enum and resource type constants in `app/modules/audit/events.py`
- Automatic event creation on organization, membership, invitation, and file operations
- Read API is org-scoped with membership verification (cross-tenant access returns 403)
- Indexed on `organization_id`, `created_at`, and `action` for query performance
- Redis caching can wrap `AuditLogService.list_events()` in a future version

**Supported events:**

| Action | Trigger |
|--------|---------|
| `ORGANIZATION_CREATED` | Organization created |
| `MEMBER_INVITED` | Invitation created |
| `INVITATION_ACCEPTED` | Invitation accepted |
| `MEMBER_ROLE_CHANGED` | Member role updated |
| `MEMBER_REMOVED` | Member removed from org |
| `OWNERSHIP_TRANSFERRED` | Ownership transferred |
| `FILE_UPLOADED` | File uploaded |
| `FILE_DOWNLOADED` | File downloaded |
| `FILE_DELETED` | File deleted |

**Example API usage:**

```bash
# List recent events
curl -H "Authorization: Bearer $TOKEN" \
     -H "X-Organization-Id: $ORG_ID" \
     "http://localhost:8000/audit-logs?page=1&page_size=20"

# Filter by action
curl -H "Authorization: Bearer $TOKEN" \
     -H "X-Organization-Id: $ORG_ID" \
     "http://localhost:8000/audit-logs?action=FILE_UPLOADED"

# Search metadata
curl -H "Authorization: Bearer $TOKEN" \
     -H "X-Organization-Id: $ORG_ID" \
     "http://localhost:8000/audit-logs/search?q=report.pdf"
```

## Testing

```bash
pytest
```

Tests use an in-memory SQLite database and do not require PostgreSQL.

## Migration commands

```bash
# Apply migrations
alembic upgrade head

# Create new migration after model changes
alembic revision --autogenerate -m "describe change"

# Rollback one revision
alembic downgrade -1
```

## Roadmap

### v1.0.0 - Initial SaaS Backend ✅
- Multi-tenant architecture with organization isolation
- JWT authentication with role-based access control
- User registration and login
- Organization creation and management
- Membership system (owner, admin, member roles)
- Invitation system for team collaboration
- File upload and management with tenant scoping
- Clean architecture with separated layers
- Database migrations with Alembic
- Comprehensive test suite

### v1.1.0 - Neon Migration ✅
- Migration support from local PostgreSQL to Neon
- Connection pool optimization for serverless
- SSL configuration for secure connections
- Migration documentation and scripts

### v1.2.0 - Streamlit Admin Dashboard ✅
- Complete Streamlit frontend
- User authentication interface
- Organization management UI
- File upload and browsing
- Invitation creation and acceptance
- User profile page
- Dashboard with statistics

### v1.3.0 - Member Management & Organization Administration ✅
- List organization members with email and role
- Change member roles (promote/demote admin)
- Remove members from organization
- Transfer organization ownership
- Role-based permission enforcement
- Member management UI in Streamlit
- Comprehensive test coverage

### v1.4.0 - File Download & File Management ✅
- File download functionality with streaming
- File deletion with RBAC enforcement
- File details endpoint with metadata
- File statistics endpoint (total files, size, average)
- Storage abstraction layer for cloud migration
- File size tracking in database
- Permission-based UI controls in Streamlit
- Comprehensive test coverage for file operations

### v1.5.0 - Audit Logs & Activity Tracking ✅
- Append-only `audit_logs` table with JSON metadata
- Centralized `AuditLogService` for event creation and queries
- Automatic audit events for org, membership, invitation, and file operations
- List endpoint with pagination and filters (action, actor, resource type, date range)
- Search endpoint (PostgreSQL-friendly ILIKE on action, resource type, metadata)
- Streamlit Audit Logs page with filters and search
- Dashboard recent activity widget (last 10 events)
- Comprehensive test coverage for audit logging

### v2.0.0 - Redis Infrastructure & Caching Layer ✅
- Redis integration for caching
- Cache-aside pattern with CacheService
- Organization list caching with invalidation
- Health check with Redis status

### v2.1.0 - Background Jobs & Task Processing ✅
- RQ (Redis Queue) integration reusing existing Redis connection
- Dedicated worker process with graceful shutdown
- Multiple queues (default, high, low)
- JobService as single enqueue interface
- Async audit log persistence
- File upload post-processing task
- Invitation processing task
- Job status API (`GET /jobs/{job_id}`)
- Health check with worker and queue status
- Streamlit Background Jobs monitoring page
- Configurable retry strategy
- Comprehensive test coverage

### v2.2.0 - Meilisearch Cloud Integration & Search Infrastructure ✅
- Full-text search on Meilisearch Cloud
- Optional search infrastructure design with graceful degradation
- Light circuit breaker to prevent blocking calls
- Automatic index setup and settings updates on startup
- Async background indexing tasks with retries and DB failure logging
- Caching integration with Redis (Cache-Aside) and selective cache invalidation
- Strict multi-tenancy boundaries enforcement via organization scoping
- Streamlit Search Dashboard displaying global and index-scoped matching results
- Mock-based unit testing covering failovers, breaker flow, caching, and APIs

### v2.3.0 - Email Infrastructure & Development Mode Fallback ✅
- Production email delivery via Resend API (`ResendProvider`)
- Graceful Development Mode fallback (`EMAIL_MODE=development`) enabling local testing without domain verification
- Automatic generation and API return of `invitation_url` and `token` for manual link sharing in development
- Streamlit UI banners and copyable invitation links for instant workflow testing
- Complete email audit logging, rate limiting, and dedicated background queue processing

### v2.4.0 - Observability Stack (Planned)
- Prometheus metrics
- Grafana dashboards
- Structured logging
- Error tracking (Sentry)

### v3.0.0 - Production Deployment (Planned)
- Docker containerization
- Kubernetes deployment
- CI/CD pipelines
- Automated backups
- Disaster recovery

### v4.0.0 - React/Next.js Frontend (Planned)
- Modern React frontend
- Next.js framework
- Real-time updates
- Mobile responsiveness
- PWA support

## Current Version

**v2.3.0** - Email Infrastructure & Development Mode Fallback

## License

MIT License - See LICENSE file for details.

