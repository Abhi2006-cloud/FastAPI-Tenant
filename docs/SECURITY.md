# Security & Threat Model

This document outlines the security architecture, tenant isolation mechanisms, threat model, and trade-offs in the **AI Workspace SaaS Backend**.

---

## 1. Multi-Tenant Isolation Architecture

The backend guarantees strict data isolation across organizations using a three-tier enforcement model:

```
[Request] -> [TenantContextMiddleware] -> [FastAPI Dependency] -> [Service Layer] -> [Repository Layer]
```

1. **Header Validation (`X-Organization-Id`)**:
   - `TenantContextMiddleware` and `get_organization_id_header` parse and validate the tenant UUID from incoming requests.
   - If missing, malformed, or invalid UUID, the request is rejected immediately with HTTP 400.

2. **Membership & Role Verification (`get_current_membership`)**:
   - Every protected tenant route requires `get_current_membership`.
   - The dependency verifies that the authenticated user (`User.id` from JWT) has an active `Membership` record matching the requested `organization_id`.
   - If no record exists, the request is rejected with HTTP 403 Forbidden.

3. **Repository-Level Filtering**:
   - Every database query for tenant data explicitly filters by `organization_id`.
   - Foreign key constraints with `ON DELETE CASCADE` ensure child entities (files, invitations, upgrade requests, audit events) are never orphaned or visible across tenant boundaries.

---

## 2. Authentication & Session Security

### Access Tokens & Revocation
- **Format**: Signed HS256 JWTs with standard claims (`sub`, `exp`, `iat`) and session tracking claims (`sid`, `jti`).
- **Session Model**: Each login creates a `UserSession` tracking client IP, user agent, device metadata, creation timestamp, and last-active timestamp.
- **Revocation Mechanisms**:
  - `POST /auth/logout`: Revokes the current session in database and immediately blacklists `sid` in Redis.
  - `POST /auth/logout-all`: Revokes all active sessions for the user across all devices.
  - `DELETE /auth/sessions/{id}`: Remote revocation of individual user sessions.
  - `POST /auth/change-password`: Automatically revokes all existing sessions and Redis blacklists to force re-authentication.
  - **Replay Attack Detection**: Refresh tokens are hashed in the database. When a refresh token rotation attempt reuses an old consumed token, the entire session is flagged as `REPLAY_ATTACK` and revoked immediately.

### Redis Fail-Open Trade-Off
In zero-cost deployments running on free-tier infrastructure (e.g. Render 512 MB and Upstash Redis):
- **Design Decision**: Token revocation checks (`revoked_session:{sid}`) and rate limiting fail **open** on Redis connection errors or timeouts.
- **Rationale**: Prioritizing service availability over strict instantaneous revocation during transient Redis cold-starts or network blips prevents total application outage.
- **Mitigation**: Access tokens have short lifespans (default 15 minutes). Even if Redis is momentarily unavailable, expired tokens are rejected by standard JWT expiration verification.

---

## 3. Rate Limiting Architecture

- **Mechanism**: Atomic Redis pipeline (`INCR` + `EXPIRE NX`) enforcing fixed-window rate limiting in a single network round-trip.
- **Applied Boundaries**:
  - `POST /auth/login`: 10 requests / minute / IP (brute-force mitigation).
  - `POST /auth/register`: 5 requests / hour / IP (abuse mitigation).
  - `POST /auth/refresh`: 30 requests / minute / IP.
  - `POST /demo/session`: 3 requests / hour / IP (demo resource preservation).
  - `POST /files/upload`: Plan-governed quota.
  - Tenant API routes: Plan-governed rate limit (e.g. 60 req/min on Free, 300 req/min on Pro).
- **Headers Returned**: Standard RFC headers:
  - `Retry-After`: Seconds remaining in current window.
  - `X-RateLimit-Limit`: Maximum allowed requests per window.
  - `X-RateLimit-Remaining`: Count of remaining permitted requests.
  - `X-RateLimit-Reset`: Unix epoch timestamp of window reset.

---

## 4. CSV Formula Injection Defense

The audit log streaming export endpoint (`GET /audit-logs/export`) implements cell sanitization:
- **Threat**: Spreadsheet applications (Excel, LibreOffice, Google Sheets) execute dynamic formulas if cell contents start with formula prefix characters.
- **Sanitization**: Any cell beginning with `=`, `+`, `-`, `@`, `\t`, or `\r` is escaped with a prepended single quote (`'`), neutralizing formula execution while preserving visual readability.

---

## 5. Ephemeral Demo Workspace Isolation

- **Demo Identifier**: Demo users are flagged with `is_demo=True` and assigned a fixed expiration (`demo_expires_at = now + DEMO_TTL_HOURS`).
- **Resource Limits**:
  - Demo creation is throttled to 3 sessions / hour / IP.
  - Total active demo users are capped by `DEMO_MAX_ACTIVE`.
- **Automatic Pruning**: `DemoService.lazy_cleanup()` runs on demo session creation, deleting expired demo workspaces, owned files, database blobs, and user records.
- **Upgrade Guard**: `POST /demo/upgrade` verifies `current_user.is_demo` and ensures the caller is the workspace owner before granting instant Pro tier evaluation.

---

## 6. Secrets & Infrastructure Sanitization

- **Credential Masking**: Database connection strings, Redis URLs, and API tokens are never printed or logged in raw form; `Settings.mask_secret()` sanitizes credentials in startup logs and health checks.
- **Platform Admin Isolation**: Administrative routes (`/admin/*`, `/jobs*`, `/email/test`) strictly verify that the caller's email is explicitly listed in `PLATFORM_ADMIN_EMAILS`. Regular tenant members receive HTTP 403.

