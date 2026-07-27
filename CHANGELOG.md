# Changelog

All notable changes to AI Workspace SaaS will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
