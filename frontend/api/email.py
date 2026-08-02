"""Frontend API functions for Email infrastructure management."""

from typing import Any, Dict, Optional

from frontend.api.client import api_client


def get_email_stats(org_id: Optional[str] = None) -> Dict[str, Any]:
    """Get delivery statistics and health for email provider."""
    params = {}
    if org_id:
        params["org_id"] = org_id
    return api_client.get("/email/stats", params=params)


def list_email_logs(
    org_id: Optional[str] = None,
    status: Optional[str] = None,
    recipient: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> Dict[str, Any]:
    """List email logs with filters."""
    params = {"limit": limit, "offset": offset}
    if org_id:
        params["org_id"] = org_id
    if status:
        params["status"] = status
    if recipient:
        params["recipient"] = recipient
    return api_client.get("/email/logs", params=params)


def send_test_email(to_email: str, subject: str, template_name: str = "welcome.html") -> Dict[str, Any]:
    """Send a test email using the email infrastructure."""
    payload = {
        "to_email": to_email,
        "subject": subject,
        "template_name": template_name,
    }
    return api_client.post("/email/test", data=payload)


def retry_email_log(log_id: str) -> Dict[str, Any]:
    """Re-queue a failed email log for retry."""
    return api_client.post(f"/email/logs/{log_id}/retry")

