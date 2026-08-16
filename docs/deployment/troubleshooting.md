# Production Troubleshooting & Maintenance Guide

This document covers common production failure scenarios, diagnostics, and recovery procedures for **AI Workspace SaaS v2.5.0**.

---

## 1. Diagnostics & Log Inspection

### Check API Liveness & Health Status
```bash
curl -i https://<BACKEND_HOST>/health
```
Expected response:
```json
{
  "status": "ok",
  "version": "2.5.0",
  "environment": "production",
  "database": "connected",
  "redis": "connected",
  "search": "connected",
  "session_store": "connected",
  "email": "connected"
}
```

If status is `"degraded"`, check individual components in the response.

---

## 2. Common Production Issues & Resolutions

### Issue A: CORS Policy Error in Browser
- **Symptom**: Browser blocks API requests with message `Access to fetch at '...' from origin '...' has been blocked by CORS policy`.
- **Cause**: `ALLOWED_ORIGINS` does not match the React frontend domain.
- **Fix**: Update `ALLOWED_ORIGINS` on Render Web Service environment settings to include the exact frontend URL (including protocol): `https://ai-workspace-frontend.onrender.com`.

### Issue B: Meilisearch Unavailable / Trial Expired
- **Symptom**: Search API endpoints return HTTP `503 Service Unavailable`, `/health` returns `"status": "degraded"`.
- **Behavior**: The FastAPI web service and RQ background worker remain fully functional for all non-search modules (Auth, Organizations, Memberships, Files, Invitations, Audit Logs).
- **Fix**: Upgrade Meilisearch Cloud plan or update `MEILISEARCH_URL` and `MEILISEARCH_API_KEY` with new credentials.

### Issue C: Database Connection Failure (Neon)
- **Symptom**: `/health` reports `"database": "disconnected"`, endpoints return HTTP 500.
- **Cause**: Database URL incorrect, SSL parameters missing, or Neon endpoint suspended.
- **Fix**:
  1. Ensure `DATABASE_URL` uses `postgresql+asyncpg://...` with `?ssl=require`.
  2. Ensure `ALEMBIC_DATABASE_URL` uses `postgresql://...` with `?sslmode=require`.
  3. Verify database connectivity in Neon console.

### Issue D: Redis Connection Failure (Upstash)
- **Symptom**: `/health` reports `"redis": "disconnected"`.
- **Cause**: Invalid password or standard `redis://` used instead of TLS `rediss://`.
- **Fix**: Verify `REDIS_URL` uses `rediss://default:password@host:port`.

---

## 3. Database Migration & Rollback Policy

- **Never Execute**: `alembic downgrade base`, `DROP DATABASE`, or `DROP TABLE`.
- **Safe Rollback Procedure**:
  1. Revert to the previous application container commit in Render.
  2. If schema changes were additive (new columns or tables), leave them in PostgreSQL to avoid data corruption.
  3. If fix is required, apply a new forward migration (`alembic revision -m "fix_issue"` -> `alembic upgrade head`).
