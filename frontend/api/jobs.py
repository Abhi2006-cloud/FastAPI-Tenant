"""Background jobs API client."""

from frontend.api.client import api_client


def get_job(job_id: str) -> dict:
    """Get status for a background job."""
    return api_client.get(f"/jobs/{job_id}")


def list_jobs(status: str | None = None, queue: str | None = None, limit: int = 50) -> dict:
    """List background jobs."""
    params: dict = {"limit": limit}
    if status:
        params["status"] = status
    if queue:
        params["queue"] = queue
    return api_client.get("/jobs", params=params)
