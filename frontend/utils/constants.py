"""Application constants and configuration for FastAPI Tenant."""

import os
from pathlib import Path

# Backend API URL - can be overridden by environment variable
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

# Page names for navigation
PAGE_LOGIN = "Login"
PAGE_REGISTER = "Register"
PAGE_DASHBOARD = "Dashboard"
PAGE_ORGANIZATIONS = "Organizations"
PAGE_MEMBERS = "Members"
PAGE_INVITATIONS = "Invitations"
PAGE_FILES = "Files"
PAGE_PROFILE = "Profile"
PAGE_AUDIT_LOGS = "Audit Logs"
PAGE_BACKGROUND_JOBS = "Background Jobs"
PAGE_SEARCH = "Search"
PAGE_EMAIL = "Email"
PAGE_SESSIONS = "Sessions"



# Session state keys
SESSION_ACCESS_TOKEN = "access_token"
SESSION_TOKEN_TYPE = "token_type"
SESSION_USER = "user"
SESSION_ORGANIZATION_ID = "organization_id"
SESSION_ORGANIZATIONS = "organizations"
SESSION_CURRENT_PAGE = "current_page"
SESSION_REFRESH_TOKEN = "refresh_token"
SESSION_SESSION_ID = "session_id"
