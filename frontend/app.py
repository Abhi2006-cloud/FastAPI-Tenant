"""Main Streamlit application entry point for FastAPI Tenant app."""

import sys
from pathlib import Path

import streamlit as st

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import importlib
import frontend.utils.constants as constants
importlib.reload(constants)

PAGE_LOGIN = getattr(constants, "PAGE_LOGIN", "Login")
PAGE_REGISTER = getattr(constants, "PAGE_REGISTER", "Register")
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

from frontend.utils.session import get_current_page, set_current_page, is_authenticated



def render_page(page_name: str):
    """Render the appropriate page based on page name."""
    if page_name == PAGE_LOGIN:
        from frontend.pages.Login import render as render_login
        render_login()
    elif page_name == PAGE_REGISTER:
        from frontend.pages.Register import render as render_register
        render_register()
    elif page_name == PAGE_DASHBOARD:
        from frontend.pages.Dashboard import render as render_dashboard
        render_dashboard()
    elif page_name == PAGE_ORGANIZATIONS:
        from frontend.pages.Organizations import render as render_organizations
        render_organizations()
    elif page_name == PAGE_MEMBERS:
        from frontend.pages.Members import render as render_members
        render_members()
    elif page_name == PAGE_INVITATIONS:
        from frontend.pages.Invitations import render as render_invitations
        render_invitations()
    elif page_name == PAGE_FILES:
        from frontend.pages.Files import render as render_files
        render_files()
    elif page_name == PAGE_PROFILE:
        from frontend.pages.Profile import render as render_profile
        render_profile()
    elif page_name == PAGE_AUDIT_LOGS:
        from frontend.pages.Audit_Logs import render as render_audit_logs
        render_audit_logs()
    elif page_name == PAGE_BACKGROUND_JOBS:
        from frontend.pages.Background_Jobs import render as render_background_jobs
        render_background_jobs()
    elif page_name == PAGE_SEARCH:
        from frontend.pages.Search import render as render_search
        render_search()
    elif page_name == PAGE_EMAIL:
        from frontend.pages.Email import render as render_email
        render_email()
    elif page_name == PAGE_SESSIONS:
        from frontend.pages.Sessions import render as render_sessions
        render_sessions()


    else:
        st.error(f"Unknown page: {page_name}")
        set_current_page(PAGE_DASHBOARD)


def main():
    """Main application entry point."""
    # Set page config
    st.set_page_config(
        page_title="AI Workspace",
        page_icon="🏢",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Initialize current page if not set
    if "current_page" not in st.session_state:
        set_current_page(PAGE_LOGIN if not is_authenticated() else PAGE_DASHBOARD)
    
    # Render sidebar
    render_sidebar()
    
    # Render current page
    current_page = get_current_page()
    render_page(current_page)



if __name__ == "__main__":
    main()
