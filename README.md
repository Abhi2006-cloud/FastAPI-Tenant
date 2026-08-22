# Multi-Tenant AI Workspace SaaS (FastAPI Backend)

A production-ready, highly scalable multi-tenant SaaS application built with **FastAPI**, **PostgreSQL**, **Redis**, **RQ Workers**, **Meilisearch**, and **Streamlit**.

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
# Terminal 1 — FastAPI Server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2 — RQ Background Worker
python -m app.jobs.worker

# Terminal 3 — Streamlit Frontend Application
cd frontend && streamlit run app.py
```

- **Interactive API Documentation (Swagger)**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Streamlit Frontend Dashboard**: [http://localhost:8501](http://localhost:8501)

---

## 🧪 Testing Suite

The application includes a 100% passing test suite of 146 unit, integration, and security tests using `pytest` and an in-memory SQLite database.

```bash
# Run all 146 tests
pytest

# Run tests with verbose output
pytest -v

# Run specific module tests
pytest app/tests/test_protected_routes.py
pytest app/tests/test_search.py
```

---

## ⚙️ CI/CD & GitHub Actions

The repository includes a automated GitHub Actions workflow defined in [`.github/workflows/ci.yml`](file:///.github/workflows/ci.yml):

- **Backend Pipeline**: Installs Python 3.12, starts Redis service container, sets environment variables (`JOB_SYNC_MODE=true`, `TEST_DATABASE_URL`), and executes `pytest`.
- **Frontend Pipeline**: Installs Node.js, runs `npm run lint` for React code formatting.
- **Docker Build Pipeline**: Builds application container images with GitHub Actions layer caching (`type=gha`).

---

## 🌐 Complete API Reference

### 🔑 Authentication (`/auth`)
| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `POST` | `/auth/register` | Register a new user account | ❌ No |
| `POST` | `/auth/login` | Authenticate user & receive JWT access token | ❌ No |
| `GET` | `/auth/me` | Retrieve profile of authenticated user | 🔐 Bearer JWT |

### 🏢 Organizations & Multi-Tenancy (`/organizations`)
| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `POST` | `/organizations` | Create a new organization/tenant | 🔐 Bearer JWT |
| `GET` | `/organizations/my` | List all organizations the user belongs to | 🔐 Bearer JWT |
| `GET` | `/organizations/{org_id}/members` | List members of an organization | 🔐 Bearer + Org Member |
| `PATCH` | `/organizations/{org_id}/members/{id}/role` | Update member role (`owner` only) | 🔐 Bearer + Org Owner |
| `DELETE` | `/organizations/{org_id}/members/{id}` | Remove member from organization | 🔐 Bearer + Org Owner |
| `POST` | `/organizations/{org_id}/transfer-ownership` | Transfer ownership to another member | 🔐 Bearer + Org Owner |

### ✉️ Invitations (`/invitations`)
| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `POST` | `/organizations/{org_id}/invite` | Create & send invitation token | 🔐 Bearer + Admin/Owner |
| `POST` | `/invitations/accept` | Accept team invitation token | 🔐 Bearer JWT |

### 📁 Files (`/files`) — *Requires `X-Organization-Id` Header*
| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `POST` | `/files/upload` | Upload file to organization storage | 🔐 Bearer + Org Member |
| `GET` | `/files` | List all files in active organization | 🔐 Bearer + Org Member |
| `GET` | `/files/stats` | Retrieve file usage statistics | 🔐 Bearer + Org Member |
| `GET` | `/files/{file_id}` | Get detailed file metadata | 🔐 Bearer + Org Member |
| `GET` | `/files/{file_id}/download` | Stream download file content | 🔐 Bearer + Org Member |
| `DELETE` | `/files/{file_id}` | Delete file (Owner/Admin or File Uploader) | 🔐 Bearer + RBAC |

### 📜 Audit Logs (`/audit-logs`) — *Requires `X-Organization-Id` Header*
| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `GET` | `/audit-logs` | Query paginated audit events with filters | 🔐 Bearer + Org Member |
| `GET` | `/audit-logs/search` | Search audit log metadata and actions | 🔐 Bearer + Org Member |

### ⚙️ Background Jobs & Health (`/jobs`, `/health`)
| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `GET` | `/health` | System health status (DB, Redis, RQ Worker, Search) | ❌ No |
| `GET` | `/jobs` | List background job execution status | 🔐 Bearer JWT |
| `GET` | `/jobs/{job_id}` | Retrieve detailed job result / error payload | 🔐 Bearer JWT |

---

## 📜 License

Distributed under the MIT License.
