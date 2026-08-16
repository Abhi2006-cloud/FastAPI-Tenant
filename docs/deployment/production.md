# Production Deployment Guide — Render Platform

This document describes how to deploy **AI Workspace SaaS v2.5.0** to Render using external managed services for PostgreSQL (Neon), Redis (Upstash), Search (Meilisearch Cloud), and Email (Resend).

---

## Architecture Diagram

```text
React Frontend (Render Static Site)
      |
      | HTTPS (REST API)
      v
FastAPI Web Service (Render Web Service - Gunicorn + Uvicorn)
      |
      +---- Neon PostgreSQL (Async runtime / Sync Alembic migrations)
      |
      +---- Upstash Redis (TLS rediss:// protocol)
      |
      +---- Meilisearch Cloud (Search queries & indexing)
      |
      +---- Resend (Transactional emails)
      |
      +---- S3 / R2 Cloud Storage (Persistent file storage)
      |
      v
RQ Background Worker (Render Background Worker - Python process)
```

---

## Step 1 — External Service Provisioning

### 1. Neon PostgreSQL
1. Create a project on [Neon.tech](https://neon.tech).
2. Create a database named `ai_workspace`.
3. Obtain the connection string:
   - **Async URL (API)**: `postgresql+asyncpg://user:pass@ep-xxx.neon.tech/ai_workspace?ssl=require`
   - **Sync URL (Alembic)**: `postgresql://user:pass@ep-xxx.neon.tech/ai_workspace?sslmode=require`

### 2. Upstash Redis
1. Create a Redis database on [Upstash.com](https://upstash.com).
2. Enable TLS support.
3. Copy the `rediss://` URL: `rediss://default:password@host:port`.

### 3. Meilisearch Cloud
1. Provision a cluster on [Meilisearch Cloud](https://www.meilisearch.com/cloud).
2. Copy the host URL (e.g. `https://ms-xxx.meilisearch.io`) and Admin API Key.
3. *Note*: If the trial period expires, the API remains alive in a degraded state and returns HTTP 503 for search endpoints without crashing the web service or background worker.

### 4. Resend Email
1. Sign up on [Resend.com](https://resend.com).
2. Verify your sending domain or use a verified sender address.
3. Generate an API Key (`re_xxx`).

---

## Step 2 — Deploying with Render Blueprint

1. Connect your GitHub repository to [Render](https://render.com).
2. Select **New** -> **Blueprint**.
3. Choose the repository containing `render.yaml`.
4. Render will parse `render.yaml` and prompt for the required environment variable secret values:
   - `DATABASE_URL`
   - `ALEMBIC_DATABASE_URL`
   - `REDIS_URL`
   - `MEILISEARCH_URL`
   - `MEILISEARCH_API_KEY`
   - `RESEND_API_KEY`
   - `EMAIL_FROM_ADDRESS`
   - `FRONTEND_URL`
   - `ALLOWED_ORIGINS`
5. Click **Apply**. Render will automatically provision:
   - FastAPI Web Service
   - RQ Background Worker
   - React Static Site

---

## Step 3 — Post-Deployment Verification

1. Verify `GET https://<BACKEND_HOST>/health` returns HTTP 200 with status `"ok"` (or `"degraded"` if Meilisearch/Email is unconfigured).
2. Verify database tables were created via Alembic (`alembic upgrade head`).
3. Open the React Static Site URL, register a new account, create an organization, invite a member, and verify complete flow.
