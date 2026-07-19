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
│   │   └── files/         # File upload and management
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

| Method | Path             | Description           |
|--------|------------------|-----------------------|
| POST   | `/files/upload`  | Upload file           |
| GET    | `/files`         | List organization files|

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

### v1.4.0 - File Download/Delete (Planned)
- File download functionality
- File deletion with permissions
- File versioning
- Storage optimization

### v1.5.0 - Audit Logs (Planned)
- Comprehensive audit logging
- User activity tracking
- Organization activity logs
- Security event logging

### v2.0.0 - Redis + Caching Layer (Planned)
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

**v1.3.0** - Member Management & Organization Administration

## License

MIT License - See LICENSE file for details.
