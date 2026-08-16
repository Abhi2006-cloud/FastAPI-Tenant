# Phase 1 — Repository Audit Document

**Application Name**: AI Workspace SaaS  
**Version**: 2.5.0  
**Audit Date**: August 2026  

---

## 1. Current Architecture Overview

```text
React Frontend (Vite SPA)
      |
      | HTTPS (REST API)
      v
FastAPI Web Service (Uvicorn / Gunicorn)
      |
      +---- Neon PostgreSQL (via asyncpg async driver / psycopg2 sync driver for Alembic)
      |
      +---- Upstash Redis (TLS rediss:// protocol)
      |
      +---- Meilisearch Cloud (REST API HTTP client)
      |
      +---- Resend Email API (HTTP client)
      |
      +---- Local Disk / S3 Object Storage (File Uploads)
      |
      v
RQ Background Worker (Python process listening to queues: high, default, low, email)
```

---

## 2. Identified Application Entry Points

| Component | Entry Point / File Path | Development Command | Production Command |
| :--- | :--- | :--- | :--- |
| **FastAPI Backend** | [`app/main.py`](file:///Users/abhisuryawanshi/Desktop/FastAPI-Tenant/app/main.py) | `uvicorn app.main:app --reload` | `gunicorn -w 4 -k uvicorn.workers.UvicornWorker app.main:app --bind 0.0.0.0:$PORT` |
| **RQ Worker** | [`app/jobs/worker.py`](file:///Users/abhisuryawanshi/Desktop/FastAPI-Tenant/app/jobs/worker.py) | `python -m app.jobs.worker` | `python -m app.jobs.worker` |
| **React Frontend** | [`frontend-react/src/main.tsx`](file:///Users/abhisuryawanshi/Desktop/FastAPI-Tenant/frontend-react/src/main.tsx) | `npm run dev` (Port 3000) | `npm ci && npm run build` (Static HTML/JS/CSS served via Render Static Site) |
| **Alembic Migrations** | [`alembic/env.py`](file:///Users/abhisuryawanshi/Desktop/FastAPI-Tenant/alembic/env.py) | `alembic upgrade head` | `alembic upgrade head` |

---

## 3. Required Infrastructure Services

1. **FastAPI Web Service** (Render Web Service - Docker container runtime)
2. **RQ Background Worker** (Render Background Worker - Docker container runtime)
3. **React Static Site** (Render Static Site hosting `frontend-react/dist`)
4. **PostgreSQL** (Neon Managed Database)
5. **Redis** (Upstash Managed TLS Redis)
6. **Search Engine** (Meilisearch Cloud - *Note: Degraded mode supported when trial ends*)
7. **Email Service** (Resend Transactional Email API)

---

## 4. Required Production Environment Variables

### Backend (`app`)
- `APP_NAME`: `AI Workspace SaaS Backend`
- `ENVIRONMENT`: `production`
- `DEBUG`: `false`
- `DATABASE_URL`: Async connection string (`postgresql+asyncpg://user:pass@ep-xxx.neon.tech/dbname?ssl=require`)
- `ALEMBIC_DATABASE_URL`: Sync connection string (`postgresql://user:pass@ep-xxx.neon.tech/dbname?sslmode=require`)
- `SECRET_KEY`: Long, randomly generated secret string for JWT signatures
- `ACCESS_TOKEN_EXPIRE_MINUTES`: `60`
- `ALGORITHM`: `HS256`
- `REDIS_URL`: Upstash TLS connection string (`rediss://default:password@host:port`)
- `MEILISEARCH_URL`: Meilisearch Cloud URL (`https://ms-xxx.meilisearch.io`)
- `MEILISEARCH_API_KEY`: Meilisearch Admin API Key
- `MEILISEARCH_INDEX_PREFIX`: `ai_workspace`
- `EMAIL_MODE`: `production`
- `EMAIL_PROVIDER`: `resend`
- `RESEND_API_KEY`: Resend API key (`re_xxx`)
- `EMAIL_FROM_NAME`: `AI Workspace`
- `EMAIL_FROM_ADDRESS`: Verified sender address (`noreply@yourdomain.com`)
- `FRONTEND_URL`: Production React site URL (`https://your-frontend.onrender.com`)
- `ALLOWED_ORIGINS`: Comma-separated CORS origins (`https://your-frontend.onrender.com`)
- `UPLOAD_DIR`: `uploads` (ephemeral disk)
- `MAX_UPLOAD_SIZE_MB`: `10`
- `INVITATION_EXPIRE_HOURS`: `72`
- `EMAIL_QUEUE_NAME`: `email`
- `EMAIL_MAX_RETRIES`: `3`
- `EMAIL_RETRY_DELAY_SECONDS`: `30`

### Frontend (`frontend-react`)
- `VITE_API_BASE_URL`: Production FastAPI URL (`https://your-backend.onrender.com`)

---

## 5. Startup Commands & Workflows

1. **Database Migration**: `alembic upgrade head`
2. **API Process**: `gunicorn -w 4 -k uvicorn.workers.UvicornWorker app.main:app --bind 0.0.0.0:$PORT`
3. **RQ Worker Process**: `python -m app.jobs.worker`
4. **React Static Build**: `npm ci && npm run build`

---

## 6. Deployment Risks & Local-Only Assumptions Identified

1. **CORS Hardcoding**: `app/main.py` hardcoded `allow_origins=["*"]`. Must be configured to validate `ALLOWED_ORIGINS` dynamically.
2. **Ephemeral Disk Storage**: Render web services wipe local storage on deployment/restart. Files saved to `./uploads` will disappear upon service restart. Cloud object storage (S3/R2) support must be provided.
3. **Meilisearch Trial Expiration**: When the Meilisearch trial expires or API fails, search endpoints must return HTTP 503 and system health should flag `"degraded"` without crashing the API or worker.
4. **Missing Gunicorn & Boto3**: Production WSGI wrapper `gunicorn` was missing from `requirements.txt`.
5. **Missing Dockerfile & Render Spec**: Repository lacked Docker container definitions and Infrastructure-as-Code (`render.yaml`).
6. **Hardcoded Secrets**: Ensure development secrets in `.env` are never baked into container images or Git repository history.
