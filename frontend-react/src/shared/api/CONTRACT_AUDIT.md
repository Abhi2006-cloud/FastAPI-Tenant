# FastAPI Backend REST API Contract Reference (v2.4.1)

This reference documents the exact contracts exposed by the FastAPI backend (`http://127.0.0.1:8000`). All frontend API services in `frontend-react/` consume these exact endpoints, models, headers, and status codes.

---

## 1. Authentication Module (`/auth`)

### `POST /auth/register`
- **Auth**: None (Public)
- **Body**: `{ email: string, password: string }`
- **Response**: `UserResponse` (`{ id: UUID, email: string, created_at: datetime }`)
- **Status Codes**: `201 Created`, `409 Conflict` (Email registered), `422 Validation Error`

### `POST /auth/login`
- **Auth**: None (Public)
- **Body**: `{ email: string, password: string }`
- **Response**: `TokenResponse` (`{ access_token: string, refresh_token: string, token_type: "bearer", session_id: UUID, expires_in: int }`)
- **Status Codes**: `200 OK`, `401 Unauthorized`, `422 Validation Error`

### `GET /auth/me`
- **Auth**: `Authorization: Bearer <access_token>`
- **Response**: `UserResponse`
- **Status Codes**: `200 OK`, `401 Unauthorized`

### `POST /auth/refresh`
- **Auth**: None (Opaque Refresh Token)
- **Body**: `{ refresh_token: string }`
- **Response**: `TokenResponse`
- **Status Codes**: `200 OK`, `401 Unauthorized`, `422 Validation Error`

### `POST /auth/logout`
- **Auth**: None
- **Body**: `{ refresh_token: string }`
- **Response**: 204 No Content
- **Status Codes**: `204 No Content`, `401 Unauthorized`

### `POST /auth/logout-all`
- **Auth**: `Authorization: Bearer <access_token>`
- **Body**: `{ refresh_token?: string, keep_current?: boolean }`
- **Response**: `{ revoked: int }`
- **Status Codes**: `200 OK`, `401 Unauthorized`

### `GET /auth/sessions`
- **Auth**: `Authorization: Bearer <access_token>`
- **Query Params**: `current_session_id?: UUID`
- **Response**: `SessionListResponse` (`{ sessions: list[SessionResponse], total: int }`)
  - `SessionResponse`: `{ id: UUID, device_name?: string, platform?: string, browser?: string, ip_address?: string, created_at: datetime, last_used_at: datetime, expires_at: datetime, is_current: bool, is_active: bool }`
- **Status Codes**: `200 OK`, `401 Unauthorized`

### `DELETE /auth/sessions/{session_id}`
- **Auth**: `Authorization: Bearer <access_token>`
- **Path Param**: `session_id: UUID`
- **Response**: 204 No Content
- **Status Codes**: `204 No Content`, `401 Unauthorized`, `404 Not Found`

---

## 2. Organizations Module (`/organizations`)

### `POST /organizations`
- **Auth**: `Authorization: Bearer <access_token>`
- **Body**: `{ name: string }`
- **Response**: `OrganizationResponse` (`{ id: UUID, name: string, owner_id: UUID, created_at: datetime }`)
- **Status Codes**: `201 Created`, `401 Unauthorized`, `422 Validation Error`

### `GET /organizations/my`
- **Auth**: `Authorization: Bearer <access_token>`
- **Response**: `list[OrganizationResponse]`
- **Status Codes**: `200 OK`, `401 Unauthorized`

### `PATCH /organizations/{org_id}`
- **Auth**: `Authorization: Bearer <access_token>`
- **Path Param**: `org_id: UUID`
- **Body**: `{ name: string }`
- **Response**: `OrganizationResponse`
- **Status Codes**: `200 OK`, `401 Unauthorized`, `403 Forbidden`, `404 Not Found`

---

## 3. Memberships Module (`/organizations/{org_id}/members`)

### `GET /organizations/{org_id}/members`
- **Auth**: `Authorization: Bearer <access_token>`
- **Path Param**: `org_id: UUID`
- **Response**: `list[MemberListResponse]` (`{ membership_id: UUID, user_id: UUID, email: string, role: "owner"|"admin"|"member", created_at: datetime }`)
- **Status Codes**: `200 OK`, `401 Unauthorized`, `403 Forbidden`

### `PATCH /organizations/{org_id}/members/{membership_id}/role`
- **Auth**: `Authorization: Bearer <access_token>`
- **Path Params**: `org_id: UUID`, `membership_id: UUID`
- **Body**: `{ role: "admin"|"member" }`
- **Response**: `RoleChangeResponse` (`{ membership_id: UUID, user_id: UUID, new_role: string }`)
- **Status Codes**: `200 OK`, `401 Unauthorized`, `403 Forbidden`

### `DELETE /organizations/{org_id}/members/{membership_id}`
- **Auth**: `Authorization: Bearer <access_token>`
- **Path Params**: `org_id: UUID`, `membership_id: UUID`
- **Response**: `MemberRemoveResponse` (`{ message: string }`)
- **Status Codes**: `200 OK`, `401 Unauthorized`, `403 Forbidden`

### `POST /organizations/{org_id}/transfer-ownership`
- **Auth**: `Authorization: Bearer <access_token>`
- **Path Param**: `org_id: UUID`
- **Body**: `{ new_owner_membership_id: UUID }`
- **Response**: `OwnershipTransferResponse` (`{ message: string }`)
- **Status Codes**: `200 OK`, `401 Unauthorized`, `403 Forbidden`

---

## 4. Invitations Module

### `POST /organizations/{org_id}/invite`
- **Auth**: `Authorization: Bearer <access_token>`
- **Path Param**: `org_id: UUID`
- **Body**: `{ email: string, role: "admin"|"member" }`
- **Response**: `InvitationResponse` (`{ id: UUID, email: string, role: string, status: string, organization_id: UUID, token?: string, invitation_url?: string, delivery_mode: string, delivery_status: string, message: string, created_at: datetime }`)
- **Status Codes**: `201 Created`, `401 Unauthorized`, `403 Forbidden`, `409 Conflict`

### `POST /invitations/accept`
- **Auth**: `Authorization: Bearer <access_token>`
- **Body**: `{ token: string }`
- **Response**: `InvitationResponse`
- **Status Codes**: `200 OK`, `401 Unauthorized`, `404 Not Found`

### `POST /invitations/{invitation_id}/resend`
- **Auth**: `Authorization: Bearer <access_token>`
- **Path Param**: `invitation_id: UUID`
- **Response**: `InvitationResponse`
- **Status Codes**: `200 OK`, `401 Unauthorized`, `403 Forbidden`

---

## 5. Files Module (`/files`)

### `POST /files/upload`
- **Auth**: `Authorization: Bearer <access_token>`, Header `X-Organization-Id: UUID`
- **Body**: `FormData(file: File)`
- **Response**: `FileResponse` (`{ id: UUID, filename: string, content_type: string, size_bytes: int, organization_id: UUID, created_at: datetime }`)
- **Status Codes**: `201 Created`, `400 Bad Request`, `401 Unauthorized`, `403 Forbidden`

### `GET /files`
- **Auth**: `Authorization: Bearer <access_token>`, Header `X-Organization-Id: UUID`
- **Response**: `list[FileResponse]`
- **Status Codes**: `200 OK`, `401 Unauthorized`, `403 Forbidden`

### `GET /files/stats`
- **Auth**: `Authorization: Bearer <access_token>`, Header `X-Organization-Id: UUID`
- **Response**: `FileStatisticsResponse` (`{ total_files: int, total_bytes: int }`)
- **Status Codes**: `200 OK`, `401 Unauthorized`, `403 Forbidden`

### `GET /files/{file_id}`
- **Auth**: `Authorization: Bearer <access_token>`, Header `X-Organization-Id: UUID`
- **Path Param**: `file_id: UUID`
- **Response**: `FileDetailResponse`
- **Status Codes**: `200 OK`, `401 Unauthorized`, `403 Forbidden`, `404 Not Found`

### `GET /files/{file_id}/download`
- **Auth**: `Authorization: Bearer <access_token>`, Header `X-Organization-Id: UUID`
- **Path Param**: `file_id: UUID`
- **Response**: Binary File Stream (`application/octet-stream`)
- **Status Codes**: `200 OK`, `401 Unauthorized`, `403 Forbidden`, `404 Not Found`

### `DELETE /files/{file_id}`
- **Auth**: `Authorization: Bearer <access_token>`, Header `X-Organization-Id: UUID`
- **Path Param**: `file_id: UUID`
- **Response**: `DeleteResponse` (`{ message: string }`)
- **Status Codes**: `200 OK`, `401 Unauthorized`, `403 Forbidden`

---

## 6. Search Module (`/search`)

### `GET /search?q=...`
- **Auth**: `Authorization: Bearer <access_token>`
- **Query Param**: `q: string`
- **Response**: `GlobalSearchResponse` (`{ query: string, mode: string, total: int, organizations: list, members: list, files: list, audit_logs: list }`)
- **Status Codes**: `200 OK`, `401 Unauthorized`

### `GET /search/{category}?q=...`
- **Auth**: `Authorization: Bearer <access_token>`
- **Path Param**: `category: "organizations"|"members"|"files"|"audit_logs"`
- **Query Param**: `q: string`
- **Response**: `SearchResponse` (`{ query: string, category: string, total: int, mode: string, items: list }`)
- **Status Codes**: `200 OK`, `401 Unauthorized`

---

## 7. Audit Module (`/audit-logs`)

### `GET /audit-logs`
- **Auth**: `Authorization: Bearer <access_token>`, Header `X-Organization-Id: UUID`
- **Query Params**: `page?: int, page_size?: int, action?: string, actor_user_id?: UUID, resource_type?: string, start_date?: datetime, end_date?: datetime`
- **Response**: `AuditLogListResponse` (`{ items: list[AuditLogResponse], total: int, page: int, page_size: int }`)
- **Status Codes**: `200 OK`, `401 Unauthorized`, `403 Forbidden`

### `GET /audit-logs/search?q=...`
- **Auth**: `Authorization: Bearer <access_token>`, Header `X-Organization-Id: UUID`
- **Query Param**: `q?: string, action?: string, resource_type?: string, page?: int, page_size?: int`
- **Response**: `AuditLogSearchResponse` (`{ items: list[AuditLogResponse], total: int, page: int, page_size: int, query: string }`)
- **Status Codes**: `200 OK`, `401 Unauthorized`, `403 Forbidden`


---

## 8. Email Module (`/email`)

### `POST /email/test`
- **Auth**: `Authorization: Bearer <access_token>`
- **Body**: `{ to_email: string, subject: string, template_name?: string, context?: dict }`
- **Response**: `EmailLogResponse` (`{ id: UUID, recipient: string, subject: string, status: string, provider: string, error_message?: string, created_at: datetime }`)
- **Status Codes**: `201 Created`, `401 Unauthorized`, `422 Validation Error`

### `GET /email/logs`
- **Auth**: `Authorization: Bearer <access_token>`
- **Query Params**: `limit?: int, offset?: int, status?: string`
- **Response**: `EmailLogListResponse` (`{ logs: list[EmailLogResponse], total: int }`)
- **Status Codes**: `200 OK`, `401 Unauthorized`

### `POST /email/logs/{log_id}/retry`
- **Auth**: `Authorization: Bearer <access_token>`
- **Path Param**: `log_id: UUID`
- **Response**: `EmailLogResponse`
- **Status Codes**: `200 OK`, `401 Unauthorized`, `404 Not Found`

### `GET /email/stats`
- **Auth**: `Authorization: Bearer <access_token>`
- **Response**: `EmailStatsResponse` (`{ total_sent: int, total_failed: int, sent_today: int, failed_today: int, provider_counts: dict }`)
- **Status Codes**: `200 OK`, `401 Unauthorized`

---

## 9. Jobs Module (`/jobs`)

### `GET /jobs`
- **Auth**: `Authorization: Bearer <access_token>`
- **Response**: `list[JobResponse]` (`{ job_id: string, task_name: string, status: string, created_at: datetime, completed_at?: datetime, error?: string }`)
- **Status Codes**: `200 OK`, `401 Unauthorized`

### `GET /jobs/{job_id}`
- **Auth**: `Authorization: Bearer <access_token>`
- **Path Param**: `job_id: string`
- **Response**: `JobResponse`
- **Status Codes**: `200 OK`, `401 Unauthorized`, `404 Not Found`

---

## 10. System Health (`/health`)

### `GET /health`
- **Auth**: None (Public)
- **Response**: `{ status: string, database: string, redis: string, search: string, session_store: string, email: string, email_detail: dict, worker: string, workers: dict, queues: dict }`
- **Status Codes**: `200 OK`
