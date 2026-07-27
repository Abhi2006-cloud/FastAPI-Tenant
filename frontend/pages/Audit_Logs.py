"""Audit Logs page."""

from datetime import datetime, time

import pandas as pd
import streamlit as st

from frontend.api.audit import list_audit_logs, search_audit_logs
from frontend.api.client import APIError
from frontend.api.memberships import list_members
from frontend.components.auth_guard import require_auth, require_organization
from frontend.utils.session import get_organization_id


AUDIT_ACTIONS = [
    "All",
    "ORGANIZATION_CREATED",
    "MEMBER_INVITED",
    "INVITATION_ACCEPTED",
    "MEMBER_ROLE_CHANGED",
    "MEMBER_REMOVED",
    "OWNERSHIP_TRANSFERRED",
    "FILE_UPLOADED",
    "FILE_DOWNLOADED",
    "FILE_DELETED",
]

RESOURCE_TYPES = ["All", "organization", "membership", "invitation", "file"]


def _format_action(action: str) -> str:
    return action.replace("_", " ").title()


def render():
    """Render the audit logs page."""
    require_auth()

    st.title("📋 Audit Logs")

    if not require_organization():
        return

    org_id = get_organization_id()

    # Build actor lookup from members
    actor_emails: dict[str, str] = {}
    try:
        members = list_members(org_id)
        actor_emails = {m["user_id"]: m["email"] for m in members}
    except APIError:
        pass

    st.subheader("Filters")
    col1, col2, col3 = st.columns(3)

    with col1:
        action_filter = st.selectbox("Action", options=AUDIT_ACTIONS, key="audit_action_filter")

    with col2:
        actor_options = {"All": None}
        for uid, email in actor_emails.items():
            actor_options[email] = uid
        selected_actor_label = st.selectbox(
            "Actor",
            options=list(actor_options.keys()),
            key="audit_actor_filter",
        )
        actor_filter = actor_options[selected_actor_label]

    with col3:
        resource_filter = st.selectbox(
            "Resource Type",
            options=RESOURCE_TYPES,
            key="audit_resource_filter",
        )

    date_col1, date_col2 = st.columns(2)
    with date_col1:
        start_date = st.date_input("Start Date", value=None, key="audit_start_date")
    with date_col2:
        end_date = st.date_input("End Date", value=None, key="audit_end_date")

    search_query = st.text_input(
        "Search",
        placeholder="Search action, resource type, or metadata...",
        key="audit_search_query",
    )

    page = st.number_input("Page", min_value=1, value=1, step=1, key="audit_page")
    page_size = st.selectbox("Page Size", options=[10, 20, 50, 100], index=1, key="audit_page_size")

    st.divider()

    try:
        with st.spinner("Loading audit logs..."):
            if search_query.strip():
                result = search_audit_logs(
                    query=search_query.strip(),
                    action=None if action_filter == "All" else action_filter,
                    resource_type=None if resource_filter == "All" else resource_filter,
                    page=page,
                    page_size=page_size,
                )
            else:
                start_dt = (
                    datetime.combine(start_date, time.min) if start_date else None
                )
                end_dt = (
                    datetime.combine(end_date, time.max) if end_date else None
                )
                result = list_audit_logs(
                    page=page,
                    page_size=page_size,
                    action=None if action_filter == "All" else action_filter,
                    actor_user_id=actor_filter,
                    resource_type=None if resource_filter == "All" else resource_filter,
                    start_date=start_dt,
                    end_date=end_dt,
                )
    except APIError as e:
        st.error(f"Failed to load audit logs: {e.message}")
        return

    items = result.get("items", [])
    total = result.get("total", 0)

    st.caption(f"Showing {len(items)} of {total} events (page {result.get('page', page)})")

    if not items:
        st.info("No audit events found for the selected filters.")
        return

    rows = []
    for item in items:
        actor_id = item.get("actor_user_id")
        actor_label = actor_emails.get(actor_id, str(actor_id) if actor_id else "System")
        rows.append(
            {
                "Timestamp": item.get("created_at", ""),
                "Actor": actor_label,
                "Action": _format_action(item.get("action", "")),
                "Resource Type": item.get("resource_type", ""),
                "Resource ID": item.get("resource_id", ""),
                "Metadata": str(item.get("metadata", {})),
            }
        )

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)
