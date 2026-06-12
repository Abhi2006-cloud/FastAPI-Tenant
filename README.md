# AI Workspace SaaS Backend

Production-style **modular monolith** multi-tenant SaaS backend built with FastAPI, PostgreSQL, and SQLAlchemy 2.0.

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

## Project structure

```
app/
├── core/           # config, database, security, dependencies, exceptions
├── middleware/     # tenant context middleware
├── modules/
│   ├── auth/
│   ├── organizations/
│   ├── memberships/
│   ├── invitations/
│   └── files/
├── utils/
├── tests/
└── main.py
alembic/            # database migrations
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

### 5. Run the API

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open interactive docs: http://localhost:8000/docs

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

- `owner` — full control
- `admin` — can invite users
- `member` — standard access

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

## Version 1 scope

Included: auth, organizations, memberships, invitations, local file storage, tenant isolation.

Not included (future versions): AI, Redis, Celery, payments, email delivery, WebSockets, microservices.

## License

MIT (adjust as needed).
