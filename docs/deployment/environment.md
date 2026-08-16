# Production Environment Variables Reference

This document lists all environment variables required to run the AI Workspace SaaS in production.

> [!WARNING]
> NEVER store plain secret values in Git, Dockerfiles, or client-side React code.

---

## Backend Environment Variables (`FastAPI` & `RQ Worker`)

| Variable Name | Description | Example / Allowed Values | Required |
| :--- | :--- | :--- | :--- |
| `APP_NAME` | Name of the backend service | `AI Workspace SaaS Backend` | Yes |
| `ENVIRONMENT` | Deployment environment | `production` \| `development` \| `test` | Yes |
| `DEBUG` | FastAPI debug mode (enables SQL logging) | `false` | Yes |
| `DATABASE_URL` | Async PostgreSQL connection string | `postgresql+asyncpg://user:pass@ep-xxx.neon.tech/dbname?ssl=require` | Yes |
| `ALEMBIC_DATABASE_URL` | Sync PostgreSQL connection string for Alembic | `postgresql://user:pass@ep-xxx.neon.tech/dbname?sslmode=require` | Yes |
| `SECRET_KEY` | JWT signature secret key | 64-character random string | Yes |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access token lifespan in minutes | `60` | Yes |
| `ALGORITHM` | JWT signing algorithm | `HS256` | Yes |
| `REDIS_URL` | Upstash TLS Redis connection URL | `rediss://default:pass@host:port` | Yes |
| `MEILISEARCH_URL` | Meilisearch Cloud endpoint | `https://ms-xxx.meilisearch.io` | Optional |
| `MEILISEARCH_API_KEY` | Meilisearch Admin API key | `ms_xxx` | Optional |
| `MEILISEARCH_INDEX_PREFIX` | Prefix for search index names | `ai_workspace` | Yes |
| `EMAIL_MODE` | Email execution mode | `production` \| `development` \| `console` | Yes |
| `EMAIL_PROVIDER` | Email provider implementation | `resend` \| `console` | Yes |
| `RESEND_API_KEY` | Resend API authorization key | `re_xxx` | Required in prod |
| `EMAIL_FROM_NAME` | Display name for outgoing emails | `AI Workspace` | Yes |
| `EMAIL_FROM_ADDRESS` | Verified domain email address | `noreply@yourdomain.com` | Yes |
| `FRONTEND_URL` | Public production React static site URL | `https://your-frontend.onrender.com` | Yes |
| `ALLOWED_ORIGINS` | Comma-separated CORS allowed origins | `https://your-frontend.onrender.com` | Yes |
| `UPLOAD_DIR` | Local storage directory path | `uploads` | Yes |
| `MAX_UPLOAD_SIZE_MB` | Maximum upload file size limit | `10` | Yes |
| `S3_ENDPOINT_URL` | Optional S3/R2 Endpoint URL | `https://<ID>.r2.cloudflarestorage.com` | Optional |
| `S3_ACCESS_KEY_ID` | Optional S3 Access Key ID | `key_id` | Optional |
| `S3_SECRET_ACCESS_KEY` | Optional S3 Secret Access Key | `secret_key` | Optional |
| `S3_BUCKET_NAME` | Optional S3 Bucket Name | `ai-workspace-uploads` | Optional |
| `INVITATION_EXPIRE_HOURS` | Lifetime of invitation tokens | `72` | Yes |

---

## Frontend Environment Variables (`React Static Site`)

| Variable Name | Description | Example / Allowed Values | Required |
| :--- | :--- | :--- | :--- |
| `VITE_API_BASE_URL` | Public base URL of the FastAPI backend | `https://your-backend.onrender.com` | Yes |
| `VITE_APP_TITLE` | App Title displayed in browser tab | `AI Workspace SaaS` | Yes |

---

## Generating Production JWT Secret

Run the following Python one-liner to generate a secure random secret key:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```
