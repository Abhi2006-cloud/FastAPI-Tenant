"""Email template registry and metadata."""

from typing import Dict, Any

TEMPLATE_INVITATION = "invitation.html"
TEMPLATE_WELCOME = "welcome.html"
TEMPLATE_PASSWORD_RESET = "password_reset.html"
TEMPLATE_EMAIL_VERIFICATION = "email_verification.html"

EMAIL_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "invitation.html": {
        "name": "Invitation",
        "description": "Sent when a user is invited to join an organization.",
        "default_subject": "You've been invited to join an organization",
        "required_vars": ["organization_name", "join_url"],
    },
    "welcome.html": {
        "name": "Welcome",
        "description": "Sent when a new user completes registration.",
        "default_subject": "Welcome to AI Workspace",
        "required_vars": ["recipient_email"],
    },
    "password_reset.html": {
        "name": "Password Reset",
        "description": "Sent when a password reset is requested.",
        "default_subject": "Reset Your Password",
        "required_vars": ["reset_url"],
    },
    "email_verification.html": {
        "name": "Email Verification",
        "description": "Sent to verify user email address.",
        "default_subject": "Verify Your Email Address",
        "required_vars": ["verify_url"],
    },
}
