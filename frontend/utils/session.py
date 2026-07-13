"""Session management utilities for Streamlit."""

import streamlit as st


def is_authenticated() -> bool:
    """Check if user is authenticated."""
    return SESSION_ACCESS_TOKEN in st.session_state


def get_access_token() -> str | None:
    """Get the current access token."""
    return st.session_state.get(SESSION_ACCESS_TOKEN)


def set_auth_data(access_token: str, token_type: str, user_data: dict) -> None:
    """Store authentication data in session state."""
    st.session_state[SESSION_ACCESS_TOKEN] = access_token
    st.session_state[SESSION_TOKEN_TYPE] = token_type
    st.session_state[SESSION_USER] = user_data


def clear_auth_data() -> None:
    """Clear all authentication data from session state."""
    keys_to_clear = [
        SESSION_ACCESS_TOKEN,
        SESSION_TOKEN_TYPE,
        SESSION_USER,
        SESSION_ORGANIZATION_ID,
        SESSION_ORGANIZATIONS,
    ]
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]


def get_user() -> dict | None:
    """Get current user data."""
    return st.session_state.get(SESSION_USER)


def get_organization_id() -> str | None:
    """Get the currently selected organization ID."""
    return st.session_state.get(SESSION_ORGANIZATION_ID)


def set_organization_id(org_id: str) -> None:
    """Set the currently selected organization ID."""
    st.session_state[SESSION_ORGANIZATION_ID] = org_id


def get_organizations() -> list | None:
    """Get the list of user's organizations."""
    return st.session_state.get(SESSION_ORGANIZATIONS)


def set_organizations(orgs: list) -> None:
    """Store the list of user's organizations."""
    st.session_state[SESSION_ORGANIZATIONS] = orgs


def get_current_page() -> str:
    """Get the current page name."""
    return st.session_state.get(SESSION_CURRENT_PAGE, PAGE_DASHBOARD)


def set_current_page(page: str) -> None:
    """Set the current page name."""
    st.session_state[SESSION_CURRENT_PAGE] = page


# Import constants
from frontend.utils.constants import (
    SESSION_ACCESS_TOKEN,
    SESSION_TOKEN_TYPE,
    SESSION_USER,
    SESSION_ORGANIZATION_ID,
    SESSION_ORGANIZATIONS,
    SESSION_CURRENT_PAGE,
    PAGE_DASHBOARD,
)
