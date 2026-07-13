"""Sidebar component for navigation and organization selection."""

import streamlit as st

from frontend.utils.constants import (
    PAGE_DASHBOARD,
    PAGE_ORGANIZATIONS,
    PAGE_INVITATIONS,
    PAGE_FILES,
    PAGE_PROFILE,
)
from frontend.utils.session import (
    get_user,
    get_organization_id,
    get_organizations,
    set_organization_id,
    clear_auth_data,
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
                clear_auth_data()
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
            (PAGE_INVITATIONS, "✉️ Invitations"),
            (PAGE_FILES, "📁 Files"),
            (PAGE_PROFILE, "👤 Profile"),
        ]
        
        for page_key, page_label in pages:
            if st.button(page_label, use_container_width=True, key=f"nav_{page_key}"):
                st.session_state.current_page = page_key
                st.rerun()
