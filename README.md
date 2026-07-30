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

The `/health` endpoint includes Redis status:

```json
{
  "status": "ok",
  "database": "connected",
  "redis": "connected"
}
```

### Future-Ready Design

The Redis infrastructure supports future features:

- **Rate Limiting**: Use `RedisService.increment()` with TTL
- **Session Storage**: Use `RedisService.json_set()` for session data
- **Background Jobs**: Use Redis queues (future implementation)
- **Distributed Locks**: Use `RedisService.set()` with NX flag
- **Real-time Features**: Use Redis pub/sub (future implementation)

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
│   │   └── audit/         # Audit logs and activity tracking
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

### 5. Run the backend API

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open interactive docs: http://localhost:8000/docs

### 6. Run the frontend (optional)

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

### v2.0.0 - Redis + Caching Layer (Completed)
- Redis integration for caching
- Session management
- Rate limiting
- Real-time features preparation

### v2.1.0 - Background Jobs (Planned)
- Celery integration
- Async task processing
- Email notifications
- Scheduled jobs

### v2.2.0 - Search (Planned)
- Full-text search
- Elasticsearch integration
- Advanced filtering
- Search analytics

### v2.3.0 - Observability Stack (Planned)
- Prometheus metrics
- Grafana dashboards
- Structured logging
- Error tracking (Sentry)

### v2.4.0 - Security Hardening (Planned)
- 2FA authentication
- OAuth/OIDC integration
- API rate limiting
- Input validation enhancements
- Security headers

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

**v1.5.0** - Audit Logs & Activity Tracking

## License

MIT License - See LICENSE file for details.
