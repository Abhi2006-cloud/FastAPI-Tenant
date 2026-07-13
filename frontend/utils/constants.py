"""Application constants and configuration."""

import os
from pathlib import Path

# Backend API URL - can be overridden by environment variable
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

# Page names for navigation
PAGE_LOGIN = "Login"
PAGE_REGISTER = "Register"
PAGE_DASHBOARD = "Dashboard"
PAGE_ORGANIZATIONS = "Organizations"
PAGE_INVITATIONS = "Invitations"
PAGE_FILES = "Files"
PAGE_PROFILE = "Profile"

# Session state keys
SESSION_ACCESS_TOKEN = "access_token"
SESSION_TOKEN_TYPE = "token_type"
SESSION_USER = "user"
SESSION_ORGANIZATION_ID = "organization_id"
SESSION_ORGANIZATIONS = "organizations"
SESSION_CURRENT_PAGE = "current_page"
