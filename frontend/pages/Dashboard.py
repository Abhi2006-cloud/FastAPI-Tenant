"""Dashboard page."""

import streamlit as st

from frontend.api.auth import get_me
from frontend.api.audit import list_audit_logs
from frontend.api.client import APIError
from frontend.api.files import list_files
from frontend.api.memberships import list_members
from frontend.api.organizations import list_my_organizations
from frontend.api.health import get_health
from frontend.components.auth_guard import require_auth
from frontend.utils.session import get_user, get_organization_id, get_organizations, set_organizations


def render():
    """Render the dashboard page."""
    require_auth()
    
    st.title("📊 Dashboard")
    
    # Load fresh data
    user = get_user()
    org_id = get_organization_id()
    organizations = get_organizations()
    
    # Fetch fresh user data
    try:
        with st.spinner("Loading your data..."):
            user_data = get_me()
            st.session_state.user = user_data
            user = user_data
    except APIError as e:
        st.error(f"Failed to load user data: {e.message}")
        return
    
    # Fetch organizations if not loaded
    if not organizations:
        try:
            with st.spinner("Loading organizations..."):
                orgs = list_my_organizations()
                set_organizations(orgs)
                organizations = orgs
        except APIError as e:
            st.error(f"Failed to load organizations: {e.message}")
    
    # Fetch files if organization is selected
    files = []
    if org_id:
        try:
            with st.spinner("Loading files..."):
                files = list_files()
        except APIError as e:
            st.error(f"Failed to load files: {e.message}")
    
    # Fetch recent audit activity if organization is selected
    recent_activity = []
    actor_emails: dict[str, str] = {}
    if org_id:
        try:
            with st.spinner("Loading recent activity..."):
                activity_result = list_audit_logs(page=1, page_size=10)
                recent_activity = activity_result.get("items", [])
                members = list_members(org_id)
                actor_emails = {m["user_id"]: m["email"] for m in members}
        except APIError:
            pass

    # Fetch health status for cache info
    redis_status = "unknown"
    try:
        health_data = get_health()
        redis_status = health_data.get("redis", "unknown")
    except APIError:
        pass

    # Display user info
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("User Email", user.get("email", "N/A"))
    
    with col2:
        st.metric("Organizations", len(organizations) if organizations else 0)
    
    with col3:
        if org_id:
            st.metric("Files in Current Org", len(files))
        else:
            st.metric("Files in Current Org", "N/A")
    
    with col4:
        redis_icon = "🟢" if redis_status == "connected" else "🔴"
        st.metric("Redis Cache", f"{redis_icon} {redis_status.title()}")
    
    st.divider()
    
    # Current organization info
    if org_id and organizations:
        current_org = None
        for org in organizations:
            if org["id"] == org_id:
                current_org = org
                break
        
        if current_org:
            st.subheader("🏢 Current Organization")
            st.info(f"**{current_org['name']}**")
    else:
        st.warning("⚠️ No organization selected. Please select an organization from the sidebar.")
    
    st.divider()

    # Recent activity
    if org_id:
        st.subheader("📋 Recent Activity")
        if recent_activity:
            for event in recent_activity:
                actor_id = event.get("actor_user_id")
                actor_label = actor_emails.get(
                    actor_id, str(actor_id) if actor_id else "System"
                )
                action_label = event.get("action", "").replace("_", " ").title()
                with st.expander(
                    f"{event.get('created_at', '')} — {action_label} by {actor_label}"
                ):
                    st.write(f"**Resource Type:** {event.get('resource_type', 'N/A')}")
                    st.write(f"**Resource ID:** {event.get('resource_id', 'N/A')}")
                    st.write(f"**Metadata:** {event.get('metadata', {})}")
        else:
            st.info("No recent activity recorded yet.")

    st.divider()

    # Recent files preview
    if files:
        st.subheader("📁 Recent Files")
        for file in files[:5]:
            with st.expander(f"📄 {file['file_name']}"):
                st.write(f"**Created:** {file['created_at']}")
                st.write(f"**Uploaded by:** {file['uploaded_by']}")
    elif org_id:
        st.info("No files uploaded yet. Go to the Files page to upload your first file.")
