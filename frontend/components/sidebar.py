"""Sidebar component for navigation and organization selection — v2.4.0."""

import streamlit as st

import importlib
import frontend.utils.constants as constants
importlib.reload(constants)

PAGE_DASHBOARD = getattr(constants, "PAGE_DASHBOARD", "Dashboard")
PAGE_ORGANIZATIONS = getattr(constants, "PAGE_ORGANIZATIONS", "Organizations")
PAGE_MEMBERS = getattr(constants, "PAGE_MEMBERS", "Members")
PAGE_INVITATIONS = getattr(constants, "PAGE_INVITATIONS", "Invitations")
PAGE_FILES = getattr(constants, "PAGE_FILES", "Files")
PAGE_PROFILE = getattr(constants, "PAGE_PROFILE", "Profile")
PAGE_AUDIT_LOGS = getattr(constants, "PAGE_AUDIT_LOGS", "Audit Logs")
PAGE_BACKGROUND_JOBS = getattr(constants, "PAGE_BACKGROUND_JOBS", "Background Jobs")
PAGE_SEARCH = getattr(constants, "PAGE_SEARCH", "Search")
PAGE_EMAIL = getattr(constants, "PAGE_EMAIL", "Email")
PAGE_SESSIONS = getattr(constants, "PAGE_SESSIONS", "Sessions")
PAGE_LOGIN = getattr(constants, "PAGE_LOGIN", "Login")


from frontend.utils.session import (
    get_user,
    get_organization_id,
    get_organizations,
    get_refresh_token,
    set_organization_id,
    clear_auth_data,
    set_current_page,
)


def render_sidebar():
    """Render the sidebar with navigation and organization selector."""
    with st.sidebar:
        st.title("AI Workspace")
        
        # User info and logout
        user = get_user()
        if user:
            st.subheader(f"👤 {user.get('email', 'User')}")

            if st.button("Logout", use_container_width=True):
                # v2.4.0: Revoke the server-side session before clearing local state
                refresh = get_refresh_token()
                if refresh:
                    try:
                        from frontend.api.auth import logout as api_logout
                        api_logout(refresh)
                    except Exception:
                        pass  # Fail silently — clear local state regardless
                clear_auth_data()
                set_current_page(PAGE_LOGIN)
                st.rerun()

            st.divider()
        
        # Organization selector
        org_id = get_organization_id()
        organizations = get_organizations() or []
        
        if organizations:
            st.subheader("🏢 Organizations")
            
            # Create organization options
            org_options = {f"{org['name']}": org['id'] for org in organizations}
            org_names = list(org_options.keys())
            
            # Find current org name
            current_org_name = None
            if org_id:
                for org in organizations:
                    if org['id'] == org_id:
                        current_org_name = org['name']
                        break
            
            # Organization selection
            selected_name = st.selectbox(
                "Select Organization",
                options=org_names,
                index=org_names.index(current_org_name) if current_org_name in org_names else 0,
                key="org_selector"
            )
            
            selected_org_id = org_options[selected_name]
            if selected_org_id != org_id:
                set_organization_id(selected_org_id)
                st.rerun()
            
            st.divider()
        
        # Navigation
        st.subheader("📋 Navigation")
        
        pages = [
            (PAGE_DASHBOARD, "📊 Dashboard"),
            (PAGE_ORGANIZATIONS, "🏢 Organizations"),
            (PAGE_MEMBERS, "👥 Members"),
            (PAGE_INVITATIONS, "✉️ Invitations"),
            (PAGE_FILES, "📁 Files"),
            (PAGE_AUDIT_LOGS, "📋 Audit Logs"),
            (PAGE_BACKGROUND_JOBS, "⚙️ Background Jobs"),
            (PAGE_SEARCH, "🔍 Search Dashboard"),
            (PAGE_EMAIL, "📧 Email Operations"),
            (PAGE_SESSIONS, "🔐 Sessions"),
            (PAGE_PROFILE, "👤 Profile"),
        ]

        for page_key, page_label in pages:
            if st.button(page_label, use_container_width=True, key=f"nav_{page_key}"):
                st.session_state.current_page = page_key
                st.rerun()
