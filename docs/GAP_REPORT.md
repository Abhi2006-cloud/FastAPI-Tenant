# Phase 2 Architecture & Implementation Gap Report

This document maps all Phase 2 backend engineering requirements (Tasks 2.1–2.6 and Backend Gaps G1–G11) to their respective endpoints, implementation files, database changes, and automated test coverage.

---

## 1. Traceability Matrix: Tasks 2.1 – 2.5

| Task ID | Component / Requirement | Endpoints / Interfaces | Implementation Files | Automated Test Suite |
| :--- | :--- | :--- | :--- | :--- |
| **Task 2.1** | **Plans & Entitlements**<br>- Single source of truth typed config<br>- Migration for `organizations.plan` & `upgrade_requests`<br>- Quota enforcement (HTTP 402)<br>- Feature locking (HTTP 402)<br>- Manual delivery for free tier invites | `GET /plans`<br>`GET /organizations/{org_id}/entitlements`<br>`POST /organizations/{org_id}/upgrade-request`<br>`GET /platform/limits`<br>`GET /admin/upgrade-requests`<br>`PATCH /admin/organizations/{org_id}/plan` | `app/modules/billing/plans.py`<br>`app/modules/billing/models.py`<br>`app/modules/billing/schemas.py`<br>`app/modules/billing/repository.py`<br>`app/modules/billing/service.py`<br>`app/modules/billing/router.py`<br>`alembic/versions/20260802_0008_phase2_plans_and_demo.py` | `app/tests/test_plans.py`<br>`app/tests/test_platform_limits.py`<br>`app/tests/test_limits_enforcement.py`<br>`app/tests/test_phase2_coverage.py` |
| **Task 2.2** | **Rate Limiting**<br>- Redis fixed-window counter<br>- Pipeline `INCR` + `EXPIRE NX`<br>- Fail-open on Redis errors<br>- Standard 429 headers (`Retry-After`, `X-RateLimit-*`) | `POST /auth/login` (10/min/IP)<br>`POST /auth/register` (5/hr/IP)<br>`POST /auth/refresh` (30/min/IP)<br>`POST /demo/session` (3/hr/IP)<br>`POST /files/upload` (plan-based)<br>General tenant routes (plan-based) | `app/core/rate_limit.py`<br>`app/core/request_context.py`<br>`app/modules/auth/router.py`<br>`app/modules/demo/router.py`<br>`app/modules/files/router.py` | `app/tests/test_rate_limit.py` |
| **Task 2.3** | **Access-Token Revocation**<br>- `sid` & `jti` in access token claims<br>- Instant Redis blacklisting on logout, logout-all, session revocation, replay attack, password change<br>- Fail-open check in `get_current_user` | `POST /auth/logout`<br>`POST /auth/logout-all`<br>`DELETE /auth/sessions/{id}`<br>`POST /auth/change-password` | `app/core/security.py`<br>`app/core/dependencies.py`<br>`app/modules/auth/service.py`<br>`app/modules/auth/router.py` | `app/tests/test_token_revocation.py`<br>`app/tests/test_sessions.py` |
| **Task 2.4** | **Backend Gaps (G1 – G11)**<br>*(See detailed matrix below)* | Multiple endpoints across orgs, members, invites, files, audit, jobs | Multiple modules in `app/modules/` | Dedicated tests across test suite |
| **Task 2.5** | **Demo Mode (Zero-Hardcoding)**<br>- `DEMO_ENABLED`, `DEMO_TTL_HOURS`, `DEMO_MAX_ACTIVE`<br>- Ephemeral workspace generation through production service path<br>- Instant demo Pro upgrade<br>- Lazy cleanup of expired demos<br>- CLI seed script | `POST /demo/session`<br>`POST /demo/upgrade`<br>CLI: `python -m app.scripts.seed_demo` | `app/modules/demo/fixtures.py`<br>`app/modules/demo/schemas.py`<br>`app/modules/demo/service.py`<br>`app/modules/demo/router.py`<br>`app/scripts/seed_demo.py` | `app/tests/test_demo.py`<br>`app/tests/test_phase2_coverage.py` |

---

## 2. Traceability Matrix: Gaps G1 – G11

| Gap ID | Description | Endpoint / Target | Implementation Details | Test Verification |
| :--- | :--- | :--- | :--- | :--- |
| **G1** | Organization Detail with Caller Metadata | `GET /organizations/{org_id}` | Returns `id`, `name`, `owner_id`, `created_at`, `plan`, `plan_updated_at`, caller `role`, and real-time `member_count`. | `app/tests/test_org_lifecycle.py::test_organization_detail_metadata`<br>`app/tests/test_phase2_coverage.py` |
| **G2** | List User Organizations with Role & Count | `GET /organizations/my` | Enriches list of caller's organizations with their specific `role` and total `member_count`. | `app/tests/test_org_lifecycle.py::test_organization_detail_metadata` |
| **G3** | List Organization Invitations | `GET /organizations/{org_id}/invitations` | Protected by owner/admin RBAC. Supports optional `?status=pending\|accepted\|revoked` filter. Masked/manual tokens handled per plan. | `app/tests/test_invitations.py::test_invitation_lifecycle`<br>`app/tests/test_phase2_coverage.py` |
| **G4** | Revoke Organization Invitation | `DELETE /organizations/{org_id}/invitations/{invitation_id}` | Protected by owner/admin RBAC. Sets invitation status to `REVOKED` and records `INVITATION_REVOKED` audit log. | `app/tests/test_invitations.py::test_invitation_lifecycle` |
| **G5** | Member Leave Organization | `POST /organizations/{org_id}/leave` | Allows non-owner members to voluntarily leave. Prevents owner from leaving (HTTP 400). Records `MEMBER_LEFT` audit log. | `app/tests/test_org_lifecycle.py::test_leave_organization` |
| **G6** | Delete Organization with Confirmation | `DELETE /organizations/{org_id}` | Requires `{ "name": "<exact_org_name>" }` in request body. Owner only. Cascades file blobs, memberships, invites, audit logs. Records `ORGANIZATION_DELETED`. | `app/tests/test_org_lifecycle.py::test_delete_organization_cascade_and_name_check` |
| **G7** | Change Password with Session Revocation | `POST /auth/change-password` | Verifies current password, enforces >= 8 characters, updates password hash, revokes all sessions in DB & Redis, returns 204. | `app/tests/test_password.py::test_change_password_and_token_invalidation`<br>`app/tests/test_phase2_coverage.py` |
| **G8** | Streaming Audit Export & Injection Guard | `GET /audit-logs/export` | Gated by `require_feature("audit_export")`. Streams CSV response. Sanitizes formulas (`=`, `+`, `-`, `@`, `\t`, `\r`) with single quote prefix. | `app/tests/test_audit_export.py::test_audit_export_feature_gate_and_csv_sanitization` |
| **G9** | Platform Admin Route Isolation | `POST /email/test`<br>`GET /jobs*` | Restricted strictly to `PLATFORM_ADMIN_EMAILS`. Regular tenant owners and members receive HTTP 403 Forbidden. | `app/tests/test_admin_endpoint_isolation.py::test_platform_admin_access_allowed_and_forbidden` |
| **G10** | Remove Dead Job / Document Upload Task | `app/jobs/tasks.py` | Removed obsolete `process_invitation_task`. Documented active `process_file_upload_task` with docstring explaining storage processing. | Code inspected and verified in `app/jobs/tasks.py`. |
| **G11** | Double-Accept Race Condition Guard | `POST /invitations/accept` | Pre-checks if user is already a member of target organization before updating status, preventing duplicate memberships or race conflicts. | `app/tests/test_phase2_coverage.py::test_invitation_service_edge_cases` |

---

## 3. Database Changes (Alembic 20260802_0008)

Migration `20260802_0008_phase2_plans_and_demo.py` adds:
1. `organizations.plan`: `VARCHAR(32)`, default `'free'`, non-nullable.
2. `organizations.plan_updated_at`: `DateTime(timezone=True)`, nullable.
3. `users.is_demo`: `BOOLEAN`, default `FALSE`, non-nullable.
4. `users.demo_expires_at`: `DateTime(timezone=True)`, nullable.
5. Table `upgrade_requests`:
   - `id`: `UUID`, primary key.
   - `organization_id`: `UUID`, FK to `organizations.id` with `ON DELETE CASCADE`.
   - `requested_by`: `UUID`, FK to `users.id` with `ON DELETE CASCADE`.
   - `requested_plan`: `VARCHAR(32)`, non-nullable.
   - `message`: `VARCHAR(1000)`, nullable.
   - `status`: `VARCHAR(32)`, default `'pending'`, non-nullable.
   - `created_at`: `DateTime(timezone=True)`, default server timestamp.

