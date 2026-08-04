# Changelog

All notable changes to AI Workspace SaaS will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.4.0] - 2026-08-02

### Added
- **Access Token + Refresh Token architecture**: Login now returns both a short-lived JWT access token (15min) and a long-lived opaque refresh token (30 days), replacing the previous single 60-minute JWT
- **Persistent session storage**: `user_sessions` PostgreSQL table stores hashed refresh tokens with device metadata — UUID PK, user FK, refresh token hash (SHA-256), device name, platform, browser, IP address, user agent, created/expires/revoked/last-used timestamps
- **Refresh Token Rotation**: `POST /auth/refresh` validates, rotates, and replaces the refresh token on every use; old token immediately invalidated
- **Replay Attack Detection**: Reuse of an already-consumed refresh token triggers `REPLAY_ATTACK` detection, immediately revokes the entire session, and returns 401
- **Session-scoped logout**: `POST /auth/logout` revokes the specific session identified by the refresh token; access token naturally expires
- **Logout all devices**: `POST /auth/logout-all` revokes all sessions for the user with optional `keep_current` to preserve the calling session
- **Session listing**: `GET /auth/sessions` returns all active sessions with device/browser/platform/IP/timestamps and `is_current` flag
- **Remote session revocation**: `DELETE /auth/sessions/{session_id}` allows remotely logging out a specific device
- **Device tracking**: Automatic browser, OS, and device name detection via `user-agents` library from User-Agent headers on login
- **Auth Audit Log**: New `auth_audit_logs` table (user-scoped, not org-scoped) logs every auth event: `LOGIN`, `LOGOUT`, `LOGOUT_ALL`, `REFRESH`, `REPLAY_ATTACK`, `SESSION_REVOKED`, `SESSION_EXPIRED`, `NEW_DEVICE_LOGIN`
- **New device email notification**: `new_device_login.html` + `.txt` Jinja2 templates; email queued fire-and-forget on login from a new device
- **Session cleanup background job**: `cleanup_expired_sessions_task` RQ task deletes expired sessions; scheduled periodically via RQ Scheduler (configurable via `SESSION_CLEANUP_INTERVAL_HOURS`)
- **`MAX_ACTIVE_SESSIONS` enforcement**: Oldest active session automatically evicted when a user's session count reaches the limit (default 20)
- **Session management Streamlit page**: New `Sessions.py` page with session cards, current device badge, per-device logout, logout-all with confirmation, and manual token rotation
- **Alembic migration** `20260802_0006_add_user_sessions_auth_audit.py`: creates both new tables with all indexes
- **New config settings**: `REFRESH_TOKEN_EXPIRE_DAYS`, `MAX_ACTIVE_SESSIONS`, `ALLOW_MULTIPLE_SESSIONS`, `ROTATE_REFRESH_TOKENS`, `REVOKE_ON_REFRESH_REPLAY`, `SESSION_CLEANUP_INTERVAL_HOURS`
- **Health endpoint** (`GET /health`) now includes `session_store` status (`connected`/`degraded`)
- **Request context helpers** (`app/core/request_context.py`): extracts client IP (X-Forwarded-For aware) and User-Agent for all auth endpoints
- **Comprehensive test suite** (`app/tests/test_sessions.py`): 15 tests covering all session lifecycle scenarios

### Changed
- `ACCESS_TOKEN_EXPIRE_MINUTES` default changed from 60 → 15 minutes (configurable)
- Login response (`TokenResponse`) extended with `refresh_token`, `session_id`, and `expires_in` fields (backward-compatible addition)
- Sidebar logout button now calls `POST /auth/logout` to revoke the server-side session before clearing local Streamlit state
- `User` model gains `sessions` relationship (cascade delete-orphan)

### Security
- Refresh tokens are cryptographically random URL-safe strings (`secrets.token_urlsafe(32)`) — never JWT, never plaintext in DB
- Only SHA-256 hashes of refresh tokens are persisted in `user_sessions.refresh_token_hash`
- Replay attacks immediately trigger session revocation across all affected sessions
- Session IDs are never exposed in URLs

## [2.3.0] - 2026-08-02


### Added
- Configurable `EMAIL_MODE` (`development`, `production`, `console`) for flexible environment behavior
- Graceful Development Mode fallback: invitations generate tokens and `invitation_url` cleanly for manual sharing without requiring domain verification
- `invitation_url`, `delivery_status`, `delivery_mode`, and `message` fields added to `InvitationResponse` payload
- Streamlit UI Development Mode warning banner and copyable invitation link input box on `frontend/pages/Invitations.py`
- Streamlit Email Dashboard (`frontend/pages/Email.py`) displaying delivery mode metrics and operational status
- Reusable Email Infrastructure (`app/infrastructure/email/`) with provider abstraction (`EmailProvider`)
- `ConsoleProvider` for local development without API quota consumption (renders & logs HTML + Plain Text to console)
- `ResendProvider` using HTTP API (`https://api.resend.com/emails`) for production delivery
- Email Audit History database table `email_logs` and Alembic migration (`20260802_0005_add_email_logs.py`)
- Dedicated Redis queue `email` (`QUEUE_EMAIL = "email"`) for background email delivery tasks
- Payload-optimized background task `process_email_job_task(email_log_id)` with exponential backoff retries (30s, 2m, 10m, 30m, 1h)
- HTML & Plain Text Jinja2 template rendering (`templates/emails/base.html`, `invitation.html`, `welcome.html`, `password_reset.html`, `email_verification.html`)
- Redis-based invitation rate limiting (default 20 invitations per organization per hour)
- Invitation idempotency (existing pending invite returned and re-sent instead of creating duplicate DB rows)
- Resend invitation endpoint `POST /invitations/{invitation_id}/resend`
- 60-second in-memory provider health caching for `GET /health` endpoint
- Streamlit Email Operations Dashboard (`frontend/pages/Email.py`) with provider metrics, audit logs, test email sender, template previewer, and manual retries
- Link-based automatic invitation acceptance in Streamlit (`http://localhost:8501/invitations?token=<token>`)
- Comprehensive offline test suite (`app/tests/test_email.py`) covering providers, template engine, rate limits, resend flow, and health integration

### Changed
- `InvitationResponse` hides raw token by default in production unless `EXPOSE_INVITATION_TOKENS=true`
- Extended `GET /health` API endpoint to report email provider status (`console`, `connected`, `misconfigured`, `degraded`)
- Updated worker script (`python -m app.jobs.worker`) to listen on `default, high, low, email` queues

## [2.2.0] - 2026-08-01


### Added
- Meilisearch Cloud integration layer (`app/infrastructure/search/`) with `SearchClient`
- Lightweight per-process in-memory Circuit Breaker to prevent excessive failed calls during outages
- Automatic index creation and settings setup (`organizations`, `members`, `files`, `audit_logs`) on startup
- Database table `search_index_failures` and Alembic migration to record failures when background retries exhaust
- Caching integration for search queries using CacheService (Cache-Aside pattern)
- Automatic search cache invalidation pattern matching `search:{org_id}:*` on document updates
- Multi-tenancy filtering to isolate search results securely by organization boundaries
- Global search endpoint (`GET /search`) and index-scoped endpoints under `app/modules/search/`
- Streamlit Search Dashboard page (`frontend/pages/Search.py`) with full-text search, highlighting, pagination, sorting, and degraded warning
- Extensive unit tests covering client connection, circuit breaker, index manager, background failures, caching, and graceful degradation

### Changed
- Extended `/health` API endpoint to report search connection status (health degrades to `status: degraded` but returns HTTP 200)
- Enqueued background indexing jobs on organization creation/rename, member addition/role-change/removal, file upload/deletion, and audit log persistence
- Expose PATCH `/organizations/{org_id}` route for organization renaming

## [2.1.0] - 2026-07-31

### Added
- RQ (Redis Queue) background job infrastructure (`app/jobs/`, `app/core/rq.py`)
- JobService as single interface for enqueue, cancel, retry, and status (`app/services/job_service.py`)
- Three priority queues: default, high, low
- Dedicated worker process (`python -m app.jobs.worker`) with graceful shutdown
- Background tasks: audit log persistence, file upload processing, invitation processing
- Job status API: `GET /jobs/{job_id}`, `GET /jobs`
- Extended `/health` with worker and queue status
- Configurable retry strategy (`RQ_RETRY_MAX`, `RQ_RETRY_INTERVALS`, `RQ_JOB_TIMEOUT`)
- Delayed job scheduling via `app/jobs/scheduler.py`
- `JOB_SYNC_MODE` for synchronous job execution in tests
- Streamlit Background Jobs page with auto-refresh
- Comprehensive test coverage in `test_jobs.py`

### Changed
- `AuditLogService.create_event()` now enqueues background jobs instead of synchronous DB writes
- File upload enqueues post-processing task after metadata is saved
- Invitation creation enqueues invitation processing task
- Updated README with RQ architecture, worker commands, and development workflow

## [2.0.0] - 2026-07-30

### Added
- Redis infrastructure layer (`app/core/redis.py`) with connection management and health checks
- RedisService with low-level Redis operations (get, set, delete, exists, expire, ttl, increment, decrement, keys, flush_namespace, json_set, json_get)
- CacheService implementing Cache-Aside pattern (get_or_set, invalidate, invalidate_pattern, set_with_ttl, get, delete)
- Centralized CacheKeyBuilder with namespaces (user, organization, membership, invitation, file, audit)
- CacheTTL constants (SHORT: 5min, MEDIUM: 15min, LONG: 1hour, VERY_LONG: 24hours, DEFAULT: 15min)
- Redis integration into FastAPI lifespan (startup connection verification, shutdown graceful close)
- Extended `/health` endpoint to include database and Redis status
- Caching for `GET /organizations/my` endpoint with Cache-Aside pattern
- Cache invalidation on organization created, membership accepted, role changed, member removed, ownership transferred
- Comprehensive logging for Redis operations (connected, disconnected, cache hit/miss, invalidation)
- Comprehensive test coverage in `test_cache.py` with mocked Redis
- Streamlit Dashboard cache statistics card showing Redis connection status
- Frontend health check API client (`frontend/api/health.py`)
- Environment variables for Redis configuration (REDIS_URL, REDIS_HOST, REDIS_PORT, REDIS_PASSWORD)

### Changed
- Updated OrganizationService to use CacheService for organization list caching
- Updated MembershipService to invalidate cache on membership changes
- Updated README with Redis architecture, Cache-Aside pattern, key naming convention, TTL strategy
- Updated project structure documentation to include cache infrastructure
- Updated tech stack to include Redis

### Fixed
- N/A

## [1.5.0] - 2026-07-21

### Added
- Audit logs module (`app/modules/audit/`) with models, repository, service, schemas, router
- `audit_logs` table with UUID PK, JSON metadata, UTC timestamps, and performance indexes
- Centralized `AuditAction` enum and resource type constants
- `AuditLogService.create_event()`, `list_events()`, and `search_events()` methods
- Automatic audit event creation for:
  - Organization creation
  - Member invitations and acceptance
  - Role changes, member removal, ownership transfer
  - File upload, download, and deletion
- `GET /audit-logs` endpoint with pagination and filters
- `GET /audit-logs/search` endpoint for PostgreSQL-friendly text search
- Alembic migration `20260721_0003_add_audit_logs`
- Streamlit Audit Logs page with action, actor, resource type, date range filters, and search
- Dashboard recent activity section (last 10 events)
- Frontend API client for audit log listing and search
- Comprehensive test coverage in `test_audit_logs.py`

### Changed
- Updated organization, invitation, membership, and file services to emit audit events
- Updated README with audit architecture, supported events, and API usage
- Updated project structure documentation to include audit module

### Fixed
- Added `self.db` to `MembershipService` so audit event hooks work correctly

## [1.4.0] - 2026-07-19

### Added
- File download endpoint with streaming support
- File deletion endpoint with RBAC enforcement
- File details endpoint with metadata and download URL
- File statistics endpoint (total files, total size, average size)
- Storage abstraction layer (StorageService) for cloud migration readiness
- File size tracking in database model
- File size column to FileRecord model
- Alembic migration for file_size column
- Repository methods: get_by_id, delete, get_statistics
- Service methods: get_file, download_file, delete_file, get_statistics
- API client methods: get_file_details, download_file, delete_file, get_file_statistics
- Streamlit Files page enhancements:
  - Storage statistics display (total files, storage used, average size)
  - File download button with save functionality
  - File deletion button with permission-based visibility
  - File size display in human-readable format
  - Permission-based UI controls (owner/admin can delete any file, members only their own)
- Comprehensive test coverage for file operations:
  - File details retrieval
  - File download success and error cases
  - Cross-tenant download prevention
  - File deletion with RBAC (owner, admin, member permissions)
  - File statistics calculation
  - Missing file error handling

### Changed
- Updated FileRecord model to include file_size column (BigInteger)
- Updated FileResponse schema to include file_size
- Updated file upload service to save file_size
- Updated file repository to use storage abstraction layer
- Enhanced Streamlit Files page with statistics and action buttons
- Updated README with file management API documentation
- Updated authorization documentation with file deletion permissions

### Fixed
- N/A

## [1.3.0] - 2026-07-14

### Added
- Organization member management endpoints
- List organization members with email and role
- Change member role (promote/demote admin)
- Remove member from organization
- Transfer organization ownership
- Role-based permission enforcement for member management
- Member management UI in Streamlit (Members page)
- API client methods for member management
- Comprehensive test coverage for member management
- PATCH method support in API client
- Member list response schema with user details
- Role change request/response schemas
- Member remove response schema
- Ownership transfer request/response schemas

### Changed
- Updated memberships router with new endpoints
- Enhanced memberships repository with list, update, delete methods
- Extended memberships service with member management logic
- Updated frontend navigation to include Members page
- Updated README with member management API documentation
- Updated authorization documentation with member management rules

### Fixed
- N/A

## [1.2.0] - 2026-07-13

### Added
- Complete Streamlit frontend application
- User authentication interface (Login/Register pages)
- Dashboard with user statistics and organization overview
- Organization management UI with creation and selection
- Invitation creation and acceptance interface
- File upload and browsing functionality
- User profile page
- API client layer with authentication and organization context
- Session state management for auth and organization context
- Reusable UI components (sidebar, auth guards)
- Error handling with user-friendly messages
- Navigation system with page routing
- Organization selector in sidebar
- Comprehensive frontend documentation

### Changed
- Updated project structure to include frontend directory
- Enhanced .env.example with frontend configuration
- Updated README with frontend setup instructions

### Fixed
- N/A

## [1.1.0] - 2026-07-13

### Added
- Neon PostgreSQL migration support
- Connection pool optimization for serverless databases
- SSL configuration for secure database connections
- Migration documentation and scripts
- Database migration analysis report

### Changed
- Updated database engine configuration with `pool_recycle=300`
- Enhanced .env.example with Neon connection examples
- Updated connection string format for SSL support

### Fixed
- N/A

## [1.0.0] - 2026-05-17

### Added
- Initial SaaS backend implementation
- Multi-tenant architecture with organization isolation
- JWT authentication with role-based access control
- User registration and login endpoints
- Organization creation and management
- Membership system (owner, admin, member roles)
- Invitation system for team collaboration
- File upload and management with tenant scoping
- Clean architecture with separated layers (router, service, repository, models, schemas)
- Database migrations with Alembic
- Comprehensive test suite with pytest
- API documentation with FastAPI auto-docs
- Tenant context middleware
- Security dependencies and authorization guards
- File upload validation and sanitization
- Email validation for invitations

### Changed
- N/A

### Fixed
- N/A

## [Unreleased]

### Planned
- Member Management (v1.3.0)
- File Download/Delete (v1.4.0)
- Audit Logs (v1.5.0)
- Redis + Caching Layer (v2.0.0)
- Background Jobs (v2.1.0)
- Search (v2.2.0)
- Observability Stack (v2.3.0)
- Security Hardening (v2.4.0)
- Production Deployment (v3.0.0)
- React/Next.js Frontend (v4.0.0)
