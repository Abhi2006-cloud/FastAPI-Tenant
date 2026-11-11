# Zero-Cost Production Deployment Checklist

Follow this ordered, checkable checklist to deploy the multi-tenant SaaS backend and React frontend at $0 cost using Neon, Upstash, Render, and Vercel.

---

### Phase 1: Neon Serverless PostgreSQL
- [ ] **Step 1.1**: Sign in to [neon.tech](https://neon.tech) and create a new project named `ai-workspace` (PostgreSQL 16 or 15).
- [ ] **Step 1.2**: Under **Connection Details**, ensure role `neondb_owner` and database `neondb` are selected.
- [ ] **Step 1.3**: Toggle **Pooled connection** ON. Copy the pooled connection string (host contains `-pooler`).
  - *This will be your `DATABASE_URL` for the application runtime (compatible with PgBouncer).*
- [ ] **Step 1.4**: Toggle **Pooled connection** OFF. Copy the direct connection string (host does NOT contain `-pooler`).
  - *This will be your `ALEMBIC_DATABASE_URL` for DDL schema migrations.*

---

### Phase 2: Upstash Serverless Redis (TCP / TLS)
- [ ] **Step 2.1**: Sign in to [upstash.com](https://upstash.com) and create a Redis database named `ai-workspace-redis`.
- [ ] **Step 2.2**: Choose the **Regional** plan in the same cloud region as Neon (e.g. `us-east-1`).
- [ ] **Step 2.3**: Under **Connect to your database**, select the **redis-cli** or **Node / Python** tab.
- [ ] **Step 2.4**: Copy the **TCP/TLS connection URL** starting with `rediss://` (e.g., `rediss://default:<PASSWORD>@<HOST>.upstash.io:6379`).
  - ⚠️ *Important: Do NOT copy the REST URL or REST tokens. The backend uses the TCP protocol for atomic Redis commands and pipelines.*

---

### Phase 3: Render Free Web Service (Docker Backend + Embedded Worker)
- [ ] **Step 3.1**: Sign in to [render.com](https://render.com) and create a **New Web Service** connected to your repository.
- [ ] **Step 3.2**: Configure the Web Service:
  - **Name**: `ai-workspace-backend`
  - **Region**: Oregon or Frankfurt
  - **Runtime**: `Docker`
  - **Dockerfile Path**: `Dockerfile`
  - **Instance Type**: `Free` (~512 MB RAM, shared CPU)
  - **Health Check Path**: `/health/live`
- [ ] **Step 3.3**: Configure the complete set of Environment Variables (as documented in `docs/DEPLOY.md`):
  ```ini
  ENVIRONMENT=production
  DATABASE_URL=<your-neon-pooled-url-with-asyncpg>
  ALEMBIC_DATABASE_URL=<your-neon-direct-url>
  REDIS_URL=<your-upstash-tcp-url-rediss://...>
  SECRET_KEY=<generate-64-char-hex-via-python-secrets>
  EMBEDDED_WORKER=true
  EMBEDDED_WORKER_QUEUES=high,default,low,email
  JOB_SYNC_MODE=false
  SEARCH_ENABLED=false
  EMAIL_MODE=development
  EMAIL_PROVIDER=console
  STORAGE_BACKEND=postgres
  MAX_UPLOAD_SIZE_MB=2
  WEB_CONCURRENCY=1
  ACCESS_TOKEN_EXPIRE_MINUTES=15
  DEMO_ENABLED=true
  PLATFORM_ADMIN_EMAILS=<your-email@example.com>
  FRONTEND_URL=https://localhost:5173
  ALLOWED_ORIGINS=https://localhost:5173
  ```
- [ ] **Step 3.4**: Click **Create Web Service** and watch the build log:
  - Verify Docker build completes.
  - Verify `alembic upgrade head` runs automatically.
  - Verify Uvicorn starts on `0.0.0.0:$PORT`.
- [ ] **Step 3.5**: Test the live endpoint in your browser or curl:
  `curl https://<YOUR_RENDER_SERVICE>.onrender.com/health/live` -> `{"status":"ok"}`.

---

### Phase 4: Vercel Hobby Deployment (React 19 SPA)
- [ ] **Step 4.1**: Sign in to [vercel.com](https://vercel.com) and click **Add New...** -> **Project**.
- [ ] **Step 4.2**: Import the repository and set:
  - **Root Directory**: `frontend-react`
  - **Framework Preset**: `Vite`
  - **Build Command**: `npm run build`
  - **Output Directory**: `dist`
- [ ] **Step 4.3**: Add Environment Variable:
  - `VITE_API_BASE_URL` = `https://<YOUR_RENDER_SERVICE>.onrender.com`
- [ ] **Step 4.4**: Click **Deploy** and copy your production Vercel URL (e.g. `https://ai-workspace.vercel.app`).

---

### Phase 5: Update CORS & Origins on Render
- [ ] **Step 5.1**: Return to your Render Web Service dashboard -> **Environment**.
- [ ] **Step 5.2**: Update:
  - `FRONTEND_URL` = `https://<YOUR_VERCEL_PROJECT>.vercel.app`
  - `ALLOWED_ORIGINS` = `https://<YOUR_VERCEL_PROJECT>.vercel.app`
- [ ] **Step 5.3**: Save changes; Render will redeploy and apply the origin headers without downtime.

---

### Phase 6: Automated Smoke Verification
- [ ] **Step 6.1**: Run the automated requests-based smoke test from your terminal against Render:
  ```bash
  python scripts/smoke_test.py https://<YOUR_RENDER_SERVICE>.onrender.com
  ```
- [ ] **Step 6.2**: Verify that all 10 checks print `PASS ✅`:
  - Liveness probe (`/health/live`)
  - Readiness probe (`/health`)
  - Demo workspace generation (`/demo/session`)
  - Entitlements & limits fetch (`/organizations/{id}/entitlements`)
  - Small file upload (`/files/upload`)
  - File retrieval & byte verification (`/files/{id}/download`)
  - Audit export 402 feature gate (`/audit-logs/export`)
  - Rate limiting burst (`/auth/login` -> 429 + `Retry-After`)
  - Session logout (`/auth/logout`)
  - Access token revocation check (`/entitlements` -> 401 Session has been revoked)

---

### Phase 7: Optional Uptime Keepalive (Prevent Render Spin-Down)
- [ ] **Step 7.1**: Sign in to [uptimerobot.com](https://uptimerobot.com) and create an **HTTP(s) Monitor**.
- [ ] **Step 7.2**: Point the URL to:
  `https://<YOUR_RENDER_SERVICE>.onrender.com/health/live`
- [ ] **Step 7.3**: Set interval to **Every 10 minutes**.
  - *This zero-cost health probe executes in <5ms without touching Postgres or Redis, preventing Render's 15-minute idle cold starts while staying well within free tier compute limits.*

---

### Phase 8: Platform Admin Verification
- [ ] **Step 8.1**: Ensure `PLATFORM_ADMIN_EMAILS` on Render includes your exact email address.
- [ ] **Step 8.2**: Open the Vercel app, navigate to `/register`, and register with that email address.
- [ ] **Step 8.3**: Navigate to `/platform` and verify that the admin tabs (Background Jobs, Email Delivery Stats, Infrastructure Metrics) appear and display live telemetry.

