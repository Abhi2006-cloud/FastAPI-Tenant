# Multi-Tenant AI Workspace SaaS (FastAPI Backend)

A production-ready, highly scalable multi-tenant SaaS application built with **FastAPI**, **PostgreSQL**, **Redis**, **RQ Workers**, and **React 19**.

---

## 🌟 Core Architecture Summary
- **Multi-Tenant Isolation**: Tenant scoping is enforced strictly at the database query layer via `organization_id`, guarded at the API gateway by `TenantContextMiddleware`, `get_organization_id_header`, and `get_current_membership` RBAC dependencies.
- **Dynamic Plan Entitlements & Quotas**: Typed single source of truth (`app/modules/billing/plans.py`) driving real-time quota enforcement in domain services (`max_members`, `max_files`, `org_storage_mb`, `invites_per_hour`) returning standard `402 Payment Required` errors (`PLAN_LIMIT_REACHED` and `PLAN_FEATURE_LOCKED`).
- **Distributed Rate Limiting**: High-performance atomic Redis fixed-window counters (`INCR` + `EXPIRE NX` pipeline) with proxy-aware IP derivation and graceful fail-open resilience, delivering standard `429 Too Many Requests`, `Retry-After`, and `X-RateLimit-*` headers.
- **Stateful JWT Revocation Denylist**: Stateless JWT access tokens carrying session IDs (`sid`) and token IDs (`jti`), paired with instant Redis denylisting on logout, password change, or remote session termination for zero-delay token revocation.
- **Zero-Cost Embedded Background Worker**: Single-process architecture featuring a daemonized RQ worker thread running inside the FastAPI web process, processing asynchronous queues (`high`, `default`, `low`, `email`) and handling graceful lifespan shutdown on Render free tier.

---

## 📐 System Architecture & Architecture Flow

The application is structured as a **Modular Monolith** adhering to Clean Architecture principles. Every component operates with strict multi-tenant data isolation.

### 🔄 1. HTTP Request Execution Flow
```
Client Request
  │
  ├─► [Middleware] TenantContextMiddleware (extracts X-Organization-Id header)
  │
  ├─► [FastAPI Router] Endpoint Handler (app/modules/<module>/router.py)
  │     │
  │     ├─► get_current_user (JWT Bearer Token verification -> app/core/dependencies.py)
  │     ├─► get_organization_id_header (Validates UUID format -> app/core/dependencies.py)
  │     └─► get_current_membership (Ensures user belongs to tenant & checks role)
  │
  ├─► [Service Layer] Business Logic & RBAC (app/modules/<module>/service.py)
  │     │
  │     ├─► [Repository Layer] Database queries (app/modules/<module>/repository.py)
  │     │     └─► AsyncSession (PostgreSQL / SQLite via SQLAlchemy 2.0)
  │     │
  │     ├─► [Cache Layer] Redis Cache-Aside (app/core/cache.py)
  │     │
  │     ├─► [Audit Service] Enqueues Audit Event (app/modules/audit/service.py)
  │     │
  │     └─► [Job Service] Enqueues Async Task (app/services/job_service.py)
  │
  └─► JSON / File Stream Response
```

### ⚡ 2. Asynchronous Background Worker Flow
```
Service Layer Call
  │
  ▼
JobService (app/services/job_service.py)
  │
  ├── JOB_SYNC_MODE=true  ──► Immediate execution on active thread (Development / pytest)
  │
  └── JOB_SYNC_MODE=false ──► Enqueue task to Redis Queue (app/core/rq.py)
                                │
                                ▼
                       [RQ Worker Process] (python -m app.jobs.worker)
                                │
                                ├─► async_runner (_execute_with_cleanup)
                                ├─► Opens dedicated AsyncSession & executes task
                                ├─► Disposes SQLAlchemy pool (engine.dispose())
                                └─► Indexes document / sends email / records audit log
```

### 🔍 3. Full-Text Search & Cache Invalidation Flow
```
Search Request ──► SearchService (app/infrastructure/search/service.py)
                       │
                       ├─► [Redis Cache Check] Cache-Aside (key: search:<org_id>:*)
                       │     ├── Cache Hit ──► Return JSON results immediately
                       │     └── Cache Miss ─► Query Meilisearch Cloud API
                       │
                       └─► [Circuit Breaker Guard] (app/infrastructure/search/client.py)
                             ├── CLOSED ──► Normal network search call to Meilisearch
                             ├── OPEN   ──► Graceful fallback (MeilisearchUnavailableException)
                             └── HALF-OPEN ► Trial request after 30s cooldown
```

---

## 🧩 Module Breakdown

| Module | Location | Primary Responsibility |
| :--- | :--- | :--- |
| **`auth`** | `app/modules/auth/` | User registration, bcrypt password hashing, JWT token generation & verification (`/auth/register`, `/auth/login`, `/auth/me`). |
| **`organizations`** | `app/modules/organizations/` | Workspace/tenant creation, listing user organizations, ownership transfer (`/organizations`). |
| **`memberships`** | `app/modules/memberships/` | Tenant role management (`owner`, `admin`, `member`), role promotion/demotion, member removal. |
| **`invitations`** | `app/modules/invitations/` | Team invitation tokens, Resend email delivery with development mode link fallback, invitation acceptance (`/invitations`). |
| **`files`** | `app/modules/files/` | Tenant-scoped file upload, streaming download, storage abstraction, RBAC deletion (`/files`). |
| **`audit`** | `app/modules/audit/` | Append-only event tracking (`FILE_UPLOADED`, `MEMBER_INVITED`, etc.), async persistence, org-scoped search (`/audit-logs`). |
| **`jobs`** | `app/modules/jobs/` | Background job status monitoring, queue statistics, job result retrieval (`/jobs`). |
| **`search`** | `app/modules/search/` | Global multi-tenant full-text search across organizations, members, files, and audit logs (`/search`). |

---

## 🛠️ Technology Stack

- **Backend Framework**: FastAPI (Python 3.12+)
- **Async Database ORM**: SQLAlchemy 2.0 + AsyncPG (PostgreSQL) / AIOSqlite (Test Environment)
- **Database Migrations**: Alembic
- **Caching & KV Storage**: Redis 7+ (`redis-py` async client)
- **Background Task Processing**: RQ (Redis Queue) with custom `ThreadPoolExecutor` async runner
- **Full-Text Search**: Meilisearch Cloud with in-memory Circuit Breaker
- **Email Infrastructure**: Resend API (`resend` SDK) with local Development Mode fallback
- **Frontend Dashboard**: Streamlit (`frontend/`) & React 19 + TypeScript (`frontend-react/`)
- **Containerization & CI/CD**: Docker, Docker Compose, GitHub Actions (`.github/workflows/ci.yml`)

---

## 🚀 Getting Started & Local Setup

### 1. Prerequisites
- **Python**: Version 3.12 or higher
- **Redis**: Local instance or Docker container running on `localhost:6379`
- **PostgreSQL**: Local PostgreSQL 14+ database or remote PostgreSQL instance

### 2. Environment Setup
```bash
# Clone the repository
git clone https://github.com/Abhi2006-cloud/FastAPI-Tenant.git
cd FastAPI-Tenant

# Create and activate virtual environment
python3.12 -m venv .venv
source .venv/bin/activate

# Install backend dependencies
pip install -r requirements.txt
```

### 3. Environment Variables
Create a `.env` file in the project root:
```ini
# Environment & Debug
ENVIRONMENT=development
DEBUG=true

# Database Connection (Async PostgreSQL)
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/ai_workspace

# JWT Security Secret
SECRET_KEY=super-secret-jwt-signing-key-change-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=60

# Redis & Background Workers
REDIS_URL=redis://localhost:6379/0
JOB_SYNC_MODE=false

# Email Configuration (Resend API)
EMAIL_MODE=development
RESEND_API_KEY=re_123456789
EMAIL_FROM=noreply@yourdomain.com

# Meilisearch Cloud (Optional)
MEILISEARCH_URL=https://ms-xxxx.meilisearch.io
MEILISEARCH_API_KEY=your-meilisearch-master-key
MEILISEARCH_INDEX_PREFIX=ai_workspace
```

### 4. Database Migrations
```bash
# Apply migrations to database
alembic upgrade head
```

### 5. Running the Application Processes

Start the 3 core backend & frontend services in separate terminal windows:

```bash
# Terminal 1 — FastAPI Server (with optional embedded background worker)
EMBEDDED_WORKER=true uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2 (Optional) — Dedicated External RQ Worker (if EMBEDDED_WORKER=false)
python -m app.jobs.worker

# Terminal 3 — React Frontend (Vite)
cd frontend-react && npm run dev
```

- **Interactive API Documentation (Swagger)**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **React Frontend**: [http://localhost:5173](http://localhost:5173)
- **Deployment Guide**: See [docs/DEPLOY.md](file:///docs/DEPLOY.md) and [docs/FREE_TIER.md](file:///docs/FREE_TIER.md) for zero-cost deployment on Render, Neon, Upstash, and Vercel.

---

## 🧪 Testing Suite

The application includes a comprehensive, 100% passing test suite of 214 unit, integration, and security tests using `pytest`, `asyncio`, and an in-memory SQLite database.

```bash
# Run all 214 tests
pytest

# Run tests with verbose output
pytest -v

# Run tests with coverage across modules and core
pytest --cov=app/modules --cov=app/core

# Run specific module tests
pytest app/tests/test_protected_routes.py
pytest app/tests/test_search.py
pytest app/tests/test_plans.py
pytest app/tests/test_rate_limit.py
```

---

## 💡 Backend Engineering Interview Talking Points

1. **Plans & Entitlements Architecture**:
   - Single source of truth typed configuration (`app/modules/billing/plans.py`) that decouples billing tiers from business logic.
   - Domain services return structured `402 Payment Required` errors (`PLAN_LIMIT_REACHED` vs `PLAN_FEATURE_LOCKED`) with actionable upgrade paths.
   - The UI never hardcodes limits or features; it dynamically queries `GET /organizations/{id}/entitlements` and adapts capabilities based on the active tier.

2. **Multi-Tenant Quota Enforcement in Services**:
   - Enforced within domain service boundaries (`router -> service -> repository`), not purely at the API middleware edge.
   - Enforces member limits, file counts, and storage byte quotas with atomic database rollbacks.
   - Uses Redis sliding/hourly counters to rate limit team invitations (`invites_per_hour`).

3. **High-Performance Distributed Rate Limiting**:
   - Atomic fixed-window counters implemented via Redis pipeline (`INCR` + `EXPIRE NX`) eliminating race conditions.
   - Real client IP resolution securely derives the true client IP from `X-Forwarded-For` using `-settings.trusted_proxy_count`, neutralizing spoofed header injection.
   - Fail-open resilience: Redis connectivity failures gracefully degrade to allow traffic rather than blocking users, logging warnings for observability.

4. **Access-Token Revocation via Session Denylist**:
   - Stateless JWT tokens contain session identifiers (`sid`) and token IDs (`jti`).
   - Logout, password changes, replay attacks, and remote device revocations immediately record the `sid` in Redis with a TTL matching the token lifespan.
   - The auth dependency checks the Redis denylist in O(1) time without querying PostgreSQL on every authenticated request.

5. **Embedded Background Worker Design**:
   - Render's free tier allows only a single web service and wipes disk storage upon sleep or redeploy.
   - Implemented an embedded, daemonized RQ worker thread running within the web process lifespan, saving the cost of a dedicated background worker.
   - Handles clean SIGTERM/lifespan shutdown, ensuring running jobs complete before container disposal.

6. **Production-Identical Demo Mode**:
   - The interactive demo (`POST /demo/session`) does not return mocked dummy objects. It provisions an ephemeral tenant workspace through the actual production service layer (`OrganizationService`, `UserService`, `FileService`, `MembershipService`).
   - Supports an instant `POST /demo/upgrade` toggle to evaluate Free vs. Pro feature gating live in the UI.

---

## ⚠️ Known Limitations (Zero-Cost Production Tier)

- **Render Cold Starts**: Render's free instance spins down into sleep mode after 15 minutes of inactivity. First requests after sleep experience a 30–60s cold start latency. *(Mitigated by setting up a free 10-minute UptimeRobot ping on `/health/live`).*
- **Database-Backed File Storage**: Files are stored in the PostgreSQL `file_blobs` table with strict quotas (2 MB per file, 50 MB Free / 200 MB Pro). This ensures uploaded files persist across ephemeral Render redeploys and spin-downs without requiring paid S3/R2 storage buckets.
- **Disabled SaaS Integrations**: Resend transactional email runs in console/manual link sharing mode (avoiding unverified domain restrictions); Meilisearch Cloud runs in degraded mode using an internal SQL ILIKE search endpoint (`GET /search/basic`).
- **Fail-Open Fault Tolerance**: If Upstash Redis experiences a network partition, the rate limiter and session token revocation fail open to prevent total application downtime, prioritizing availability while logging alerts.

---

## ⚙️ CI/CD & GitHub Actions

The repository includes a automated GitHub Actions workflow defined in [`.github/workflows/ci.yml`](file:///.github/workflows/ci.yml):

- **Backend Pipeline**: Installs Python 3.12, starts Redis service container, sets environment variables (`JOB_SYNC_MODE=true`, `TEST_DATABASE_URL`), and executes `pytest`.
- **Frontend Pipeline**: Installs Node.js, runs `npm run lint` for React code formatting.
- **Docker Build Pipeline**: Builds application container images with GitHub Actions layer caching (`type=gha`).

---

## 🌐 Complete API Reference

### 🔑 Authentication & Sessions (`/auth`)
| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `POST` | `/auth/register` | Register a new user account | ❌ No |
| `POST` | `/auth/login` | Authenticate user & receive JWT access token | ❌ No |
| `POST` | `/auth/refresh` | Rotate refresh token & receive new access token | ❌ No |
| `GET` | `/auth/me` | Retrieve profile of authenticated user | 🔐 Bearer JWT |
| `POST` | `/auth/logout` | Revoke active session in DB and Redis | 🔐 Bearer JWT |
| `POST` | `/auth/logout-all` | Revoke all active sessions across all devices | 🔐 Bearer JWT |
| `POST` | `/auth/change-password` | Change password & invalidate all other sessions | 🔐 Bearer JWT |
| `GET` | `/auth/sessions` | List active sessions with current device flag | 🔐 Bearer JWT |
| `DELETE` | `/auth/sessions/{id}` | Remote revocation of specific session | 🔐 Bearer JWT |

### 💳 Plans & Billing (`/plans`, `/organizations/{org_id}`, `/admin`)
| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `GET` | `/plans` | List available plans, limits, and feature availability | ❌ No |
| `GET` | `/platform/limits` | Infrastructure free-tier constraints and limits | ❌ No |
| `GET` | `/organizations/{org_id}/entitlements` | Real-time usage, limits, and feature access | 🔐 Bearer + Org Member |
| `POST` | `/organizations/{org_id}/upgrade-request` | Request plan upgrade from workspace owner/admin | 🔐 Bearer + Admin/Owner |
| `GET` | `/admin/upgrade-requests` | List tenant upgrade requests | 🔐 Platform Admin |
| `PATCH` | `/admin/organizations/{org_id}/plan` | Update organization subscription tier | 🔐 Platform Admin |

### 🚀 Ephemeral Demo (`/demo`)
| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `POST` | `/demo/session` | Create zero-cost ephemeral workspace with demo fixtures | ❌ No (Rate-limited) |
| `POST` | `/demo/upgrade` | Instant evaluation upgrade to Pro tier for demo workspaces | 🔐 Bearer (Demo Owner) |

### 🏢 Organizations & Multi-Tenancy (`/organizations`)
| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `POST` | `/organizations` | Create a new organization/tenant | 🔐 Bearer JWT |
| `GET` | `/organizations/my` | List all organizations caller belongs to with role & count | 🔐 Bearer JWT |
| `GET` | `/organizations/{org_id}` | Organization detail with caller role & member count | 🔐 Bearer + Org Member |
| `POST` | `/organizations/{org_id}/leave` | Member leaves organization voluntarily | 🔐 Bearer + Member/Admin |
| `DELETE` | `/organizations/{org_id}` | Delete organization with exact name confirmation | 🔐 Bearer + Org Owner |
| `GET` | `/organizations/{org_id}/members` | List members of an organization | 🔐 Bearer + Org Member |
| `PATCH` | `/organizations/{org_id}/members/{id}/role` | Update member role (`owner` only) | 🔐 Bearer + Org Owner |
| `DELETE` | `/organizations/{org_id}/members/{id}` | Remove member from organization | 🔐 Bearer + Org Owner |
| `POST` | `/organizations/{org_id}/transfer-ownership` | Transfer ownership to another member | 🔐 Bearer + Org Owner |

### ✉️ Invitations (`/invitations`)
| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `POST` | `/organizations/{org_id}/invite` | Create & send invitation (manual token on Free tier) | 🔐 Bearer + Admin/Owner |
| `GET` | `/organizations/{org_id}/invitations` | List organization invitations with optional status filter | 🔐 Bearer + Admin/Owner |
| `DELETE` | `/organizations/{org_id}/invitations/{id}` | Revoke pending invitation | 🔐 Bearer + Admin/Owner |
| `POST` | `/invitations/accept` | Accept team invitation token (with double-accept guard) | 🔐 Bearer JWT |

### 📁 Files (`/files`) — *Requires `X-Organization-Id` Header*
| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `POST` | `/files/upload` | Upload file to storage (quota enforced) | 🔐 Bearer + Org Member |
| `GET` | `/files` | List all files in active organization | 🔐 Bearer + Org Member |
| `GET` | `/files/stats` | Retrieve file usage statistics | 🔐 Bearer + Org Member |
| `GET` | `/files/{file_id}` | Get detailed file metadata | 🔐 Bearer + Org Member |
| `GET` | `/files/{file_id}/download` | Stream download file content | 🔐 Bearer + Org Member |
| `DELETE` | `/files/{file_id}` | Delete file (Owner/Admin or File Uploader) | 🔐 Bearer + RBAC |

### 📜 Audit Logs (`/audit-logs`) — *Requires `X-Organization-Id` Header*
| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `GET` | `/audit-logs` | Query paginated audit events with plan-bounded history | 🔐 Bearer + Org Member |
| `GET` | `/audit-logs/export` | Stream CSV audit log export with formula sanitization | 🔐 Bearer + Feature Gated |
| `GET` | `/audit-logs/search` | Search audit log metadata and actions | 🔐 Bearer + Org Member |

### ⚙️ Background Jobs & Health (`/jobs`, `/health`)
| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `GET` | `/health` | System health status (DB, Redis, RQ Worker, Search) | ❌ No |
| `GET` | `/health/live` | Instant liveness probe for UptimeRobot / Render keep-alive | ❌ No |
| `GET` | `/jobs` | List background job execution status | 🔐 Platform Admin |
| `GET` | `/jobs/{job_id}` | Retrieve detailed job result / error payload | 🔐 Platform Admin |

---

## 📜 License

Distributed under the MIT License.
