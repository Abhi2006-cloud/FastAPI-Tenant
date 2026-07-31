"""Background Jobs admin page."""

from datetime import timedelta

import streamlit as st

from frontend.api.client import APIError
from frontend.api.health import get_health
from frontend.api.jobs import get_job, list_jobs
from frontend.components.auth_guard import require_auth

REFRESH_SECONDS = 5


def _status_badge(status: str) -> str:
    icons = {
        "queued": "🟡",
        "started": "🔵",
        "finished": "🟢",
        "failed": "🔴",
    }
    return f"{icons.get(status, '⚪')} {status.title()}"


def _render_jobs_panel() -> None:
    try:
        health = get_health()
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Redis", health.get("redis", "unknown").title())
        with col2:
            st.metric("Worker", health.get("worker", "unknown").title())
        with col3:
            queues = health.get("queues", {})
            total_queued = sum(q.get("queued", 0) for q in queues.values())
            st.metric("Queued Jobs", total_queued)
    except APIError as e:
        st.error(f"Failed to load health status: {e.message}")
        return

    st.divider()

    tab_queued, tab_running, tab_completed, tab_failed = st.tabs(
        ["Queued", "Running", "Completed", "Failed"]
    )

    for tab, status in [
        (tab_queued, "queued"),
        (tab_running, "started"),
        (tab_completed, "finished"),
        (tab_failed, "failed"),
    ]:
        with tab:
            try:
                result = list_jobs(status=status, limit=50)
                jobs = result.get("items", [])
            except APIError as e:
                st.error(f"Failed to load jobs: {e.message}")
                continue

            if not jobs:
                st.info(f"No {status} jobs.")
                continue

            for job in jobs:
                with st.expander(
                    f"{_status_badge(job.get('status', ''))} — {job.get('job_id', 'N/A')}"
                ):
                    st.write(f"**Queue:** {job.get('queue', 'N/A')}")
                    st.write(f"**Created:** {job.get('created_at', 'N/A')}")
                    st.write(f"**Started:** {job.get('started_at', 'N/A')}")
                    st.write(f"**Finished:** {job.get('finished_at', 'N/A')}")
                    if job.get("result"):
                        st.write(f"**Result:** {job.get('result')}")
                    if job.get("error"):
                        st.error(job.get("error"))

    st.caption(f"Auto-refreshes every {REFRESH_SECONDS} seconds")


def render():
    """Render the background jobs monitoring page."""
    require_auth()

    st.title("⚙️ Background Jobs")

    # Prefer Streamlit fragments for non-blocking auto-refresh when available
    if hasattr(st, "fragment"):
        @st.fragment(run_every=timedelta(seconds=REFRESH_SECONDS))
        def auto_jobs_panel() -> None:
            _render_jobs_panel()

        auto_jobs_panel()
    else:
        _render_jobs_panel()
        if st.button("Refresh", key="jobs_manual_refresh"):
            st.rerun()

    st.divider()
    st.subheader("Job Lookup")
    job_id = st.text_input("Job ID", placeholder="Enter job ID to inspect")
    if job_id and st.button("Fetch Job Details"):
        try:
            st.json(get_job(job_id))
        except APIError as e:
            st.error(f"Job lookup failed: {e.message}")
