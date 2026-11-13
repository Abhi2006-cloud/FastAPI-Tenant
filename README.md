# Multi-Tenant AI Workspace SaaS

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-19.2+-61DAFB?style=flat-square&logo=react&logoColor=black)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0+-3178C6?style=flat-square&logo=typescript&logoColor=white)](https://www.typescriptlang.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-AsyncPG-336791?style=flat-square&logo=postgresql&logoColor=white)](https://www.postgresql.org)
[![Redis](https://img.shields.io/badge/Redis-7+-DC382D?style=flat-square&logo=redis&logoColor=white)](https://redis.io)
[![Python](https://img.shields.io/badge/Python-3.12+-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-4.0+-38B2AC?style=flat-square&logo=tailwind-css&logoColor=white)](https://tailwindcss.com)
[![Tests](https://img.shields.io/badge/Tests-214_Passed_100%25-brightgreen?style=flat-square&logo=pytest&logoColor=white)](https://docs.pytest.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](LICENSE)

A production-ready, highly scalable multi-tenant SaaS application built with **FastAPI**, **PostgreSQL (AsyncPG)**, **Redis**, **RQ Asynchronous Workers**, and **React 19 (TypeScript + Vite + Tailwind CSS)**.

Designed around Clean Architecture and Modular Monolith principles, the platform provides strict tenant isolation, role-based access control (RBAC), multi-device session management with instant token revocation, distributed atomic rate limiting, decoupled background task execution, and full-text search with circuit breaker failover.

---

## 📸 Platform Preview

| Workspace Overview | Team Members & Roles |
| :---: | :---: |
| ![Overview Dashboard](docs/screens/overview-desktop.png) | ![Member Management](docs/screens/members-desktop.png) |

| Cloud File Storage | Plans & Subscription Entitlements |
| :---: | :---: |
| ![File Storage](docs/screens/files-desktop.png) | ![Billing & Plans](docs/screens/billing-desktop.png) |

---

## 🌟 Key Features

### 🏢 Strict Multi-Tenant Isolation
- Tenant context is extracted and validated at the edge by `TenantContextMiddleware` via `X-Organization-Id`.
- Every database query is strictly scoped by `organization_id` using asynchronous SQLAlchemy 2.0 and `asyncpg`.
- Granular Role-Based Access Control (`owner`, `admin`, `member`) prevents privilege escalation, safeguards owner records, and orchestrates transactional ownership transfer.

### 🔐 Enterprise Session Security & Token Revocation
- Dual-token lifecycle: short-lived JWT access tokens paired with long-lived, rotating refresh tokens stored as SHA-256 digests in `user_sessions`.
- Real-time device and user-agent fingerprinting with per-device active session lists.
- Instant access token revocation via an atomic Redis denylist on logout, password change, or remote session termination.
- Automatic replay attack detection immediately revokes compromised session chains.

### 💳 Dynamic Subscription Entitlements & Feature Gating
- Centralized typed plan definitions (`Free`, `Pro`, `Enterprise`) enforce organizational quotas (`max_members`, `max_files`, `org_storage_mb`, `invites_per_hour`).
- Standardized `402 Payment Required` responses return machine-readable error codes (`PLAN_LIMIT_REACHED`, `PLAN_FEATURE_LOCKED`) with upgrade prompts.
- Interactive client components adapt dynamically by querying `GET /organizations/{id}/entitlements`.

### ⏱️ High-Performance Distributed Rate Limiting
- Atomic fixed-window counters implemented via Redis pipelines (`INCR` + `EXPIRE NX`) eliminate race conditions.
- True client IP derivation from `X-Forwarded-For` using reverse proxy trust offsets (`trusted_proxy_count`), neutralizing header injection.
- Fail-open resilience: Redis connectivity partitions gracefully degrade to prioritize platform availability while capturing operational logs.

### ⚡ Decoupled Background Task Processing
- Redis Queue (RQ) worker subsystem executes heavy I/O operations out-of-band:
  - Audit log persistence with actor metadata.
  - Multi-mode transactional email delivery (Resend API with development console fallback).
  - Search document indexing and cache invalidation.
- Supports both a standalone worker daemon (`python -m app.jobs.worker`) and an embedded worker thread for unified single-container deployments.
- Dedicated `NullPool` database sessions ensure background tasks never leak connections across distinct asyncio event loops.

### 🔍 Resilient Search Engine with Circuit Breaker
- Multi-tenant full-text search with Meilisearch Cloud integration.
- Three-state in-memory Circuit Breaker (`CLOSED`, `OPEN`, `HALF_OPEN`) automatically bypasses degraded search endpoints and directs queries to database fallback search (`GET /search/basic`).

---

## 📐 System Architecture & Request Flows

### 🔄 1. HTTP Request Execution Pipeline
```
Client Request (React SPA / API Client)
  │
  ├─► [CORS Middleware] Origin & Header Validation
  │
  ├─► [Tenant Middleware] TenantContextMiddleware (extracts & sets X-Organization-Id ContextVar)
  │
  ├─► [FastAPI Router] Route Handler (app/modules/<module>/router.py)
  │     │
  │     ├─► get_current_user (JWT Bearer Token verification + Redis Revocation Check)
  │     ├─► get_organization_id_header (UUID validation & tenant scope check)
  │     └─► get_current_membership (RBAC hierarchy & permission enforcement)
  │
  ├─► [Service Layer] Business Logic & Plan Quotas (app/modules/<module>/service.py)
  │     │
  │     ├─► [Repository Layer] Async database queries (app/modules/<module>/repository.py)
  │     │     └─► PostgreSQL via SQLAlchemy 2.0 AsyncSession
  │     │
  │     ├─► [Cache Layer] Redis Cache-Aside with automated invalidation (app/core/cache.py)
  │     │
  │     ├─► [Job Service] Non-blocking task dispatch to Redis Queue (app/services/job_service.py)
  │     │
  │     └─► [Audit Service] Enqueues immutable audit events
  │
  └─► JSON / Streaming Response
```

### ⚡ 2. Asynchronous Background Worker Architecture
```
FastAPI Service
  │
  └─► Enqueue Job ──► Redis Queue (high / default / low / email)
                        │
                        ▼
               [RQ Worker Subsystem]
                        │
                        ├─► Dedicated worker engine (NullPool)
                        ├─► Executes isolated task in ephemeral event loop
                        ├─► Closes DB connection immediately on task completion
                        └─► Updates job status & emits telemetry
```

---

## 🧩 Modular Monolith Structure

```
FastAPI-Tenant/
├── app/
│   ├── core/                         # Core infrastructure & configuration
│   │   ├── config.py                 # Pydantic v2 application settings & environment validation
│   │   ├── database.py               # Async SQLAlchemy engine, NullPool worker engine & sessions
│   │   ├── dependencies.py           # Authentication, tenant header, and membership guards
│   │   ├── redis.py                  # Async Redis connection pool and health checks
│   │   ├── rq.py                     # Sync Redis connection & queue provider for RQ workers
│   │   ├── security.py               # Password hashing (bcrypt) and JWT encoding/decoding
│   │   └── cache.py                  # Cache-aside utilities, key builders, and TTL tiers
│   ├── infrastructure/               # External cloud service integrations
│   │   ├── email/                    # Resend API driver, console provider & Jinja2 templates
│   │   └── search/                   # Meilisearch client, circuit breaker & index mappers
│   ├── jobs/                         # Asynchronous worker tasks & schedulers
│   │   ├── tasks.py                  # Audit logging tasks and file processing
│   │   ├── email_tasks.py            # Transactional email delivery and exponential retries
│   │   ├── search_tasks.py           # Document indexing and deletion tasks
│   │   ├── embedded_worker.py        # In-process daemonized RQ worker thread
│   │   └── worker.py                 # Dedicated standalone RQ worker process entry point
│   ├── middleware/                   # Starlette & FastAPI request middleware
│   │   └── tenant.py                 # Request-scoped organization context provider
│   ├── modules/                      # Domain feature modules
│   │   ├── auth/                     # Registration, login, session store & device detection
│   │   ├── organizations/            # Tenant lifecycle, ownership transfer & metadata
│   │   ├── memberships/              # Member roles, promotions, demotions & removal
│   │   ├── invitations/              # Token-based team invitations & email dispatch
│   │   ├── files/                    # Tenant asset storage, streaming downloads & quotas
│   │   ├── audit/                    # Immutable event logs & CSV export
│   │   ├── billing/                  # Subscription plans, quotas & upgrade requests
│   │   ├── demo/                     # Ephemeral production-identical sandbox workspaces
│   │   └── search/                   # Tenant-isolated full-text search endpoints
│   ├── main.py                       # Application initialization, routers & lifespan management
│   └── tests/                        # Comprehensive test suite (214 tests)
├── frontend-react/                   # Modern React 19 Single Page Application
│   ├── src/
│   │   ├── pages/                    # Workspace views (Overview, Members, Files, Audit, Billing)
│   │   ├── layout/                   # Sidebar navigation, organization switcher & header
│   │   ├── shared/                   # Axios client, AuthContext, OrgContext, Toast & UI components
│   │   └── test/                     # Vitest test suite for UI components and hooks
│   ├── vite.config.ts                # Vite bundler configuration
│   └── package.json                  # React 19 dependencies & build scripts
├── alembic/                          # Database schema migration revisions
├── Dockerfile                        # Multi-stage production container image
├── render.yaml                       # Infrastructure-as-code deployment specification
└── requirements.txt                  # Python production dependencies
```

---

## 🛠️ Technology Stack

| Domain | Technology | Version | Purpose |
| :--- | :--- | :--- | :--- |
| **Backend API** | FastAPI | `0.115+` | High-performance asynchronous web framework |
| **Language** | Python | `3.12+` | Core backend runtime |
| **Database ORM** | SQLAlchemy | `2.0+` | Async ORM with Declarative Models |
| **Database Driver** | asyncpg | `0.30+` | Asynchronous PostgreSQL driver |
| **Schema Migrations**| Alembic | `1.14+` | Database version control & migrations |
| **In-Memory Store** | Redis (with hiredis) | `7+` | Token denylist, distributed rate limiting, and cache-aside |
| **Task Queue** | RQ (Redis Queue) | `2.1+` | Asynchronous task offloading & worker management |
| **Search Engine** | Meilisearch Cloud | REST API | Lexical typo-tolerant full-text search with circuit breaker |
| **Email Service** | Resend API / Jinja2 | REST API | Transactional invitations & security notifications |
| **Frontend Framework**| React | `19.2+` | Modern Single Page Application |
| **Frontend Tooling** | Vite / TypeScript | `Vite 6 / TS 5` | Build optimization, fast HMR, and type safety |
| **State Management** | TanStack React Query | `5.100+` | Server state management, auto-caching, and refetching |
| **Styling & UI** | Tailwind CSS / Lucide | `Tailwind 4` | Responsive utility-first design system |
| **Testing** | pytest / Vitest | Latest | 100% automated test coverage across backend & frontend |

---

## 🚀 Getting Started & Local Development

### 1. Prerequisites
- **Python**: Version `3.12` or higher
- **Node.js**: Version `20` or higher (with `npm`)
- **Redis**: Local instance or Docker container on port `6379`
- **PostgreSQL**: Local instance or remote database (PostgreSQL 14+)

### 2. Backend Setup
```bash
# Clone repository
git clone https://github.com/Abhi2006-cloud/FastAPI-Tenant.git
cd FastAPI-Tenant

# Create and activate Python virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install backend dependencies
pip install -r requirements.txt
```

### 3. Environment Configuration
Create a `.env` file in the project root:
```ini
# Core Configuration
ENVIRONMENT=development
DEBUG=true
SECRET_KEY=generate-a-secure-random-32-char-secret-key-here
ACCESS_TOKEN_EXPIRE_MINUTES=60

# Database (PostgreSQL with asyncpg driver)
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/ai_workspace

# Redis & Background Processing
REDIS_URL=redis://localhost:6379/0
JOB_SYNC_MODE=false
EMBEDDED_WORKER=true

# Transactional Email (Resend or Console Mode)
EMAIL_MODE=development
EMAIL_PROVIDER=console
RESEND_API_KEY=
EMAIL_FROM=noreply@yourdomain.com

# Full-Text Search (Optional Meilisearch Cloud)
SEARCH_ENABLED=false
MEILISEARCH_URL=
MEILISEARCH_API_KEY=
MEILISEARCH_INDEX_PREFIX=ai_workspace
```

### 4. Database Migrations
```bash
# Run migrations up to latest revision
alembic upgrade head
```

### 5. Frontend Setup
```bash
cd frontend-react
npm install
```

### 6. Running Application Services
Start the development servers:

```bash
# Terminal 1 — FastAPI Server (with embedded RQ worker)
source .venv/bin/activate
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# Terminal 2 — React 19 Frontend (Vite)
cd frontend-react
npm run dev
```

- **React Application**: [http://localhost:5173](http://localhost:5173)
- **FastAPI Interactive Docs (Swagger)**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health Check Endpoint**: [http://localhost:8000/health](http://localhost:8000/health)

---

## 🧪 Automated Testing Suite

The repository features comprehensive, 100% passing test coverage across both backend services and frontend components.

```bash
# Run all backend tests (214 tests)
pytest -v

# Run backend tests with coverage report
pytest --cov=app/modules --cov=app/core

# Run specific domain test suites
pytest app/tests/test_auth.py
pytest app/tests/test_organizations.py
pytest app/tests/test_protected_routes.py
pytest app/tests/test_jobs.py
pytest app/tests/test_plans.py

# Run frontend tests (Vitest)
cd frontend-react
npm run test

# Run frontend production build check
npm run build
```

---

## 🌐 API Reference

### 🔑 Authentication & Sessions (`/auth`)
| Method | Endpoint | Description | Access |
| :--- | :--- | :--- | :--- |
| `POST` | `/auth/register` | Register a new user account | Public |
| `POST` | `/auth/login` | Authenticate and issue JWT access & refresh tokens | Public |
| `POST` | `/auth/refresh` | Rotate refresh token and issue new access token | Public |
| `GET` | `/auth/me` | Fetch authenticated user profile | Bearer JWT |
| `POST` | `/auth/logout` | Revoke current session in database and Redis | Bearer JWT |
| `POST` | `/auth/logout-all` | Revoke all active sessions across all devices | Bearer JWT |
| `POST` | `/auth/change-password` | Update password and invalidate all other sessions | Bearer JWT |
| `GET` | `/auth/sessions` | List active user sessions with device metadata | Bearer JWT |
| `DELETE` | `/auth/sessions/{id}` | Remote revocation of a specific device session | Bearer JWT |

### 🏢 Organizations & Workspaces (`/organizations`)
| Method | Endpoint | Description | Access |
| :--- | :--- | :--- | :--- |
| `POST` | `/organizations` | Create a new tenant workspace | Bearer JWT |
| `GET` | `/organizations/my` | List workspaces user belongs to with role & count | Bearer JWT |
| `GET` | `/organizations/{org_id}` | Retrieve organization details and caller role | Tenant Member |
| `POST` | `/organizations/{org_id}/leave` | Voluntarily leave organization | Tenant Member |
| `DELETE` | `/organizations/{org_id}` | Delete organization with exact-name confirmation | Tenant Owner |
| `GET` | `/organizations/{org_id}/members` | List members and their assigned roles | Tenant Member |
| `PATCH` | `/organizations/{org_id}/members/{id}/role` | Update member role (`admin`, `member`) | Tenant Owner |
| `DELETE` | `/organizations/{org_id}/members/{id}` | Remove member from workspace | Tenant Owner |
| `POST` | `/organizations/{org_id}/transfer-ownership` | Transfer workspace ownership | Tenant Owner |

### ✉️ Team Invitations (`/invitations`)
| Method | Endpoint | Description | Access |
| :--- | :--- | :--- | :--- |
| `POST` | `/organizations/{org_id}/invite` | Create and dispatch workspace invitation | Admin / Owner |
| `GET` | `/organizations/{org_id}/invitations` | List organization invitations by status | Admin / Owner |
| `DELETE` | `/organizations/{org_id}/invitations/{id}` | Revoke pending invitation | Admin / Owner |
| `POST` | `/invitations/accept` | Accept invitation token and join workspace | Bearer JWT |

### 📁 Files & Storage (`/files`)
*Requires `X-Organization-Id` tenant header*
| Method | Endpoint | Description | Access |
| :--- | :--- | :--- | :--- |
| `POST` | `/files/upload` | Upload file (enforces plan storage & file size quotas) | Tenant Member |
| `GET` | `/files` | List all files in active workspace | Tenant Member |
| `GET` | `/files/stats` | Retrieve workspace storage utilization metrics | Tenant Member |
| `GET` | `/files/{file_id}` | Fetch file metadata | Tenant Member |
| `GET` | `/files/{file_id}/download` | Stream download file content | Tenant Member |
| `DELETE` | `/files/{file_id}` | Delete file | File Uploader / Admin / Owner |

### 📜 Audit Logs (`/audit-logs`)
*Requires `X-Organization-Id` tenant header*
| Method | Endpoint | Description | Access |
| :--- | :--- | :--- | :--- |
| `GET` | `/audit-logs` | Query paginated audit events with action filters | Tenant Member |
| `GET` | `/audit-logs/export` | Stream CSV audit log export with formula sanitization | Feature Gated (Pro+) |
| `GET` | `/audit-logs/search` | Search audit log actions and metadata | Tenant Member |

### 💳 Plans & Subscription Entitlements (`/plans`, `/organizations/{org_id}`)
| Method | Endpoint | Description | Access |
| :--- | :--- | :--- | :--- |
| `GET` | `/plans` | List available subscription tiers, limits, and features | Public |
| `GET` | `/platform/limits` | Retrieve platform-wide limits and configurations | Public |
| `GET` | `/organizations/{org_id}/entitlements` | Fetch real-time tenant quotas, usage, and gated features | Tenant Member |
| `POST` | `/organizations/{org_id}/upgrade-request` | Submit tier upgrade request | Admin / Owner |
| `GET` | `/admin/upgrade-requests` | List tenant upgrade requests across platform | Platform Admin |
| `PATCH` | `/admin/organizations/{org_id}/plan` | Update organization subscription tier | Platform Admin |

### 🚀 Ephemeral Demo Environment (`/demo`)
| Method | Endpoint | Description | Access |
| :--- | :--- | :--- | :--- |
| `POST` | `/demo/session` | Create ephemeral workspace with pre-populated fixtures | Rate-Limited Public |
| `POST` | `/demo/upgrade` | Toggle demo workspace between Free and Pro tiers | Demo Owner |

### ⚙️ Health & Monitoring (`/health`, `/jobs`)
| Method | Endpoint | Description | Access |
| :--- | :--- | :--- | :--- |
| `GET` | `/health` | Deep health check (Database, Redis, Worker, Search) | Public |
| `GET` | `/health/live` | Instant liveness probe for load balancers & uptime monitors | Public |
| `GET` | `/jobs` | List execution status of background tasks | Platform Admin |
| `GET` | `/jobs/{job_id}` | Retrieve detailed background job result or error payload | Platform Admin |

---

## 📄 License

Distributed under the MIT License. See [LICENSE](LICENSE) for details.
