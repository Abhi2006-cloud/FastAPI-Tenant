# Production Deployment Guide (Zero-Cost Free Tier)

This guide provides exact click-by-click instructions to deploy the AI Workspace SaaS backend and React frontend at zero cost using **Neon**, **Upstash**, **Render**, and **Vercel**.

---

## Architecture Summary
- **Database**: Neon Serverless PostgreSQL (Free)
- **Cache & Queues**: Upstash Redis (Free TCP/TLS)
- **API & Worker**: Render Free Web Service (Single Docker container running FastAPI + Embedded RQ Worker)
- **Frontend SPA**: Vercel Hobby (React 19 + Vite Static Site)
- **Uptime Pinger**: UptimeRobot (Free 5-minute HTTP check)

---

## Step 1: Provision Neon Serverless PostgreSQL

1. Navigate to [neon.tech](https://neon.tech) and sign up / log in with GitHub.
2. Click **Create Project**:
   - **Name**: `ai-workspace`
   - **Postgres version**: `16` or `15`
   - **Region**: Select closest to your users (e.g., `AWS US East (Ohio) - us-east-2`).
3. In the project dashboard under **Connection Details**:
   - Select database `neondb` and role `neondb_owner`.
   - Toggle **Pooled connection** ON. Copy this URL (host contains `-pooler`). This will be `DATABASE_URL`.
   - Toggle **Pooled connection** OFF. Copy this URL (direct host without `-pooler`). This will be `ALEMBIC_DATABASE_URL`.
   - Note: asyncpg driver format is `postgresql+asyncpg://...`. The application automatically sanitizes `sslmode` and handles connection arguments.

---

## Step 2: Provision Upstash Serverless Redis

1. Navigate to [upstash.com](https://upstash.com) and sign up / log in.
2. Click **Create Database**:
   - **Name**: `ai-workspace-redis`
   - **Type**: Regional (select same cloud/region as Neon, e.g., `us-east-1`).
   - **Eviction**: Disabled.
3. In the database dashboard, scroll to **Connect to your database**:
   - Select the **redis-cli** or **Node / Python** tab.
   - Locate the **TCP TLS URL** starting with `rediss://`.
   - Example format: `rediss://default:<PASSWORD>@<HOST>.upstash.io:6379`.
   - **Do NOT** use the REST URL or REST tokens. Copy this TCP URL; it will be `REDIS_URL`.

---

## Step 3: Deploy Backend on Render (Free Web Service)

1. Navigate to [render.com](https://render.com) and log in with GitHub.
2. Click **New +** -> **Web Service**.
3. Connect your repository: `FastAPI-Tenant`.
4. Configure the service:
   - **Name**: `ai-workspace-backend`
   - **Region**: Oregon (or nearest region)
   - **Runtime**: `Docker`
   - **Dockerfile Path**: `Dockerfile`
   - **Instance Type**: `Free`
   - **Start Command**: (Inherited from `Dockerfile` / `render.yaml`)
     ```bash
     sh -c "alembic upgrade head && gunicorn -w ${WEB_CONCURRENCY:-1} -k uvicorn.workers.UvicornWorker app.main:app --bind 0.0.0.0:$PORT --timeout 120"
     ```
   - **Health Check Path**: `/health/live`
5. Under **Environment Variables**, add the variables from the table below:

### Complete Backend Environment Variables Table

| Key | Example Value | Description |
| :--- | :--- | :--- |
| `ENVIRONMENT` | `production` | Enforces production security checks |
| `DATABASE_URL` | `postgresql+asyncpg://neondb_owner:...@ep-cool-pooler.us-east-2.aws.neon.tech/neondb?ssl=require` | Pooled Neon host (PgBouncer) |
| `ALEMBIC_DATABASE_URL` | `postgresql://neondb_owner:...@ep-cool-direct.us-east-2.aws.neon.tech/neondb?sslmode=require` | Direct Neon host for DDL migrations |
| `SECRET_KEY` | *(Generate 64-char hex)* | `python -c "import secrets; print(secrets.token_hex(32))"` |
| `REDIS_URL` | `rediss://default:...@tight-guppy-90698.upstash.io:6379` | Upstash TCP/TLS connection URL |
| `EMBEDDED_WORKER` | `true` | Starts embedded RQ worker in background daemon thread |
| `EMBEDDED_WORKER_QUEUES` | `high,default,low,email` | Queues processed by the embedded worker |
| `JOB_SYNC_MODE` | `false` | Asynchronous job execution via Redis |
| `SEARCH_ENABLED` | `false` | Bypasses Meilisearch to avoid expired trial failures |
| `EMAIL_MODE` | `development` | Enables safe in-app invitation links |
| `EMAIL_PROVIDER` | `console` | Zero-cost logging; does not degrade health status |
| `STORAGE_BACKEND` | `postgres` | Persists files in `file_blobs` table (survives container spin-down) |
| `MAX_UPLOAD_SIZE_MB` | `2` | Maximum upload size for free tier |
| `WEB_CONCURRENCY` | `1` | Strictly 1 Gunicorn process to conserve 512 MB memory |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `15` | JWT session access token expiration |
| `DEMO_ENABLED` | `true` | Enables sample demo workflows |
| `PLATFORM_ADMIN_EMAILS` | `admin@example.com` | Platform administration seed accounts |
| `FRONTEND_URL` | `https://ai-workspace.vercel.app` | URL of the deployed Vercel frontend |
| `ALLOWED_ORIGINS` | `https://ai-workspace.vercel.app` | Allowed CORS origins (must not be `*` in production) |

6. Click **Create Web Service**.
7. Render will build the Docker image, run migrations (`alembic upgrade head`), and boot the server.
8. Verify deployment by visiting `https://<YOUR_RENDER_SERVICE>.onrender.com/health`.
   Expected response:
   ```json
   {
     "status": "ok",
     "version": "2.5.0",
     "environment": "production",
     "database": "connected",
     "redis": "connected",
     "search": "disabled",
     "email": "console",
     "worker": {
       "mode": "embedded",
       "alive": true,
       "status": "running",
       "queues": ["high", "default", "low", "email"]
     }
   }
   ```

---

## Step 4: Deploy Frontend on Vercel (Hobby Tier)

1. Navigate to [vercel.com](https://vercel.com) and log in with GitHub.
2. Click **Add New...** -> **Project**.
3. Import the `FastAPI-Tenant` repository.
4. Configure Project Settings:
   - **Root Directory**: Click Edit, select `frontend-react`.
   - **Framework Preset**: `Vite`.
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
   - **Install Command**: `npm install`
5. In **Environment Variables**:
   - `VITE_API_BASE_URL`: `https://<YOUR_RENDER_SERVICE>.onrender.com`
6. Click **Deploy**.
7. Copy the assigned Vercel URL (e.g., `https://ai-workspace.vercel.app`).
8. Return to your Render backend service dashboard -> **Environment** and update:
   - `FRONTEND_URL` = `https://ai-workspace.vercel.app`
   - `ALLOWED_ORIGINS` = `https://ai-workspace.vercel.app`
   - Save changes (Render will trigger a quick reload).

---

## Step 5: Setup UptimeRobot (Prevent Render Cold Starts)

Render free web services sleep after 15 minutes of inactivity. To keep the service warm at zero cost:
1. Navigate to [uptimerobot.com](https://uptimerobot.com) and create a free account.
2. Click **Add New Monitor**:
   - **Monitor Type**: `HTTP(s)`
   - **Friendly Name**: `AI Workspace Health Ping`
   - **URL (or IP)**: `https://<YOUR_RENDER_SERVICE>.onrender.com/health/live`
   - **Monitoring Interval**: `Every 10 minutes`
3. Click **Create Monitor**.
4. The lightweight `/health/live` endpoint responds with `{"status":"ok"}` in < 5 ms and makes **zero database or Redis calls**, keeping your Render web service awake without burning Neon compute hours or Upstash Redis command quotas.

