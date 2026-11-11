# Zero-Cost Free-Tier Deployment Architecture

This document details the exact infrastructure footprint, resource limits, cold-start handling, and operational characteristics of the AI Workspace SaaS backend running at **$0.00 / month**.

---

## 1. Component Topology & Service Distribution

```
                              ┌────────────────────────┐
                              │  Vercel Hobby (Static) │
                              │   React 19 Frontend    │
                              └───────────┬────────────┘
                                          │ HTTPS
                                          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ Render Free Web Service (Single Container, 512 MB RAM, Ephemeral Disk)      │
│                                                                             │
│   ┌────────────────────────────────┐   ┌────────────────────────────────┐  │
│   │ FastAPI Web Application        │   │ Embedded RQ SimpleWorker       │  │
│   │ (1 Uvicorn Worker via Gunicorn)│◄──┤ (1 Daemon Thread, in-process)  │  │
│   └───────────────┬────────────────┘   └───────────────┬────────────────┘  │
└───────────────────┼────────────────────────────────────┼────────────────────┘
                    │                                    │
         TCP/TLS    │                         TCP/TLS    │
   ┌────────────────┴───────────────┐     ┌──────────────┴──────────────────┐
   │ Neon Serverless PostgreSQL     │     │ Upstash Serverless TLS Redis     │
   │ (PgBouncer Pooler + BYTEA blob)│     │ (10k cmds/sec, rediss:// URL)   │
   └────────────────────────────────┘     └─────────────────────────────────┘
```

| Component | Provider / Tier | Host Type | Primary Role |
| :--- | :--- | :--- | :--- |
| **Frontend** | Vercel (Hobby) | Edge CDN (Static) | React 19 + TypeScript SPA |
| **Backend Web** | Render (Free) | Web Service (Docker) | FastAPI REST API (`WEB_CONCURRENCY=1`) |
| **Background Worker** | Render (Free) | Daemon Thread | Embedded RQ worker (`EMBEDDED_WORKER=true`) |
| **Database** | Neon (Free) | Serverless PostgreSQL | Relational tenant data + `file_blobs` |
| **Cache & Queues**| Upstash (Free) | Serverless Redis (TCP) | Queues (`high`, `default`, `low`, `email`) + cache |
| **Uptime Pinger** | UptimeRobot (Free) | Periodic HTTP Monitor | Pings `/health/live` every 10 min |

---

## 2. Hard Limits & Operational Constraints

### Render Free Web Service
- **RAM**: ~512 MB shared. Gunicorn is restricted to a single worker (`-w 1`) to eliminate memory pressure.
- **CPU**: Shared vCPU.
- **Spin-Down**: Sleeps after **15 minutes** of HTTP inactivity.
- **Filesystem**: **Ephemeral**. The local filesystem is wiped on redeploy, container restart, and sleep cycle. Local disk storage (`STORAGE_BACKEND=local`) must NOT be used for persistent files.
- **Worker Services**: Background worker services are disabled on the Render Free plan. All background task processing runs inside the web container via the embedded worker thread.

### Neon Free PostgreSQL
- **Storage**: ~0.5 GB.
- **Compute**: Autosuspends when idle; cold starts take ~5 to 15 seconds.
- **PgBouncer Pooling**: The pooled connection endpoint (host ending in `-pooler`) operates in transaction pooling mode.
  - Prepared statements fail behind transaction poolers unless `statement_cache_size=0` is set.
  - `asyncpg` rejects the `sslmode` and `channel_binding` query parameters; these are automatically stripped by `build_database_connection_params()` and configured via `connect_args={'ssl': 'require'}`.
  - Connection timeout is set to 30s to absorb Neon compute wake-up latency.
  - Connection pool is sized conservatively (`DB_POOL_SIZE=3`, `DB_MAX_OVERFLOW=2`, `pool_recycle=300`).

### Upstash Redis Free Tier
- **Commands**: 10,000 commands/second cap.
- **Storage**: 250 MB max data size, 100 MB max record size. Total Redis footprint is kept under 5 MB.
- **Protocol**: Direct TCP/TLS (`rediss://`) connection format is used. The HTTP REST URL and tokens are **not** used.
- **Bandwidth**: 10 GB monthly bandwidth allowance.

---

## 3. Idle Redis Chatter & Worker Tuning

Running an RQ worker typically incurs Redis polling traffic. To keep command consumption well under Upstash free-tier allowances:
- **Worker Type**: `EmbeddedSimpleWorker` (subclass of RQ `SimpleWorker`) avoids process forking (`os.fork()`) inside a multithreaded web application.
- **Signals**: Signal handler registration is bypassed (`_install_signal_handlers()` is a no-op) to avoid Python thread-safety exceptions.
- **Timeouts**: `TimerDeathPenalty` replaces `UnixSignalDeathPenalty` (which relies on `SIGALRM`).
- **Dequeue Timeout**: Set to **15 seconds** (`dequeue_timeout=15`).
- **Measured Chatter**:
  - Steady-state idle command rate: **~4 to 8 commands per minute** (consisting of blocking queue pops `BLMOVE`/`BLPOP` every 15s and periodic worker heartbeat).
  - Total monthly idle commands: `~8 cmds/min * 60 min * 720 hours = ~345,600 commands/month` (well below Upstash limits).
  - Startup / registration overhead: ~50 one-time setup commands.

---

## 4. Cold-Start Behavior

1. **Idle State**: After 15 minutes of zero inbound traffic, Render sleeps the container and Neon suspends database compute.
2. **First Inbound Request**:
   - Render boots the Docker container: **~30 to 50 seconds**.
   - Container startup runs `alembic upgrade head`, starts Gunicorn, runs `validate_production_settings()`, connects to Redis, and launches the embedded worker daemon thread.
   - The first request touching Postgres triggers Neon compute wake-up: **~5 to 10 seconds** (absorbed by the 30s connection timeout).
3. **Frontend Experience**:
   - The React frontend displays an active connection indicator with retry logic on cold starts.
4. **Preventing Cold Starts (Optional)**:
   - Configure a free UptimeRobot HTTP monitor to hit `GET /health/live` every 10 minutes.
   - `GET /health/live` returns `{"status": "ok"}` **instantly** without executing database queries or Redis commands, keeping Render awake while consuming zero Neon compute hours or Upstash quotas.

---

## 5. Disabled Features & Zero-Cost Replacements

| Subsystem | Status | Reason & Zero-Cost Architecture |
| :--- | :--- | :--- |
| **Meilisearch** | **Disabled** (`SEARCH_ENABLED=false`) | Meilisearch Cloud trial expired. Rather than failing continuously or filling failure logs, search initialization and task enqueueing are cleanly bypassed. `/health` reports `search: "disabled"` and overall status stays `"ok"`. |
| **Email (Resend)**| **Console Mode** (`EMAIL_PROVIDER=console`) | Real email delivery requires a paid or custom verified domain. In console mode, invitation tokens and verification links are output directly to backend logs and API payloads without degrading `/health`. |
| **Disk Storage** | **PostgreSQL Backend** (`STORAGE_BACKEND=postgres`)| Render free tier disks are wiped on container restart. Files are persisted as binary `BYTEA` blobs in the PostgreSQL `file_blobs` table (max 2 MB per file via `MAX_UPLOAD_SIZE_MB=2`), ensuring uploads survive redeployments and spin-downs. |

