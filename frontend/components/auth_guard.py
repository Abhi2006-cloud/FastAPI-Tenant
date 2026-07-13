"""Authentication guard component."""

import streamlit as st

from frontend.utils.constants import PAGE_LOGIN
from frontend.utils.session import is_authenticated


def require_auth():
    """Redirect to login page if not authenticated."""
    if not is_authenticated():
        st.warning("Please login to access this page.")
        st.session_state.current_page = PAGE_LOGIN
        st.rerun()


def require_organization():
    """Check if organization is selected, show warning if not."""
    from frontend.utils.session import get_organization_id
    
    org_id = get_organization_id()
    if not org_id:
        st.warning("⚠️ Please select an organization first from the sidebar.")
        return False
    return True
