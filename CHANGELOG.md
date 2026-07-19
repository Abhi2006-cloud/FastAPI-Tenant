# Changelog

All notable changes to AI Workspace SaaS will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
