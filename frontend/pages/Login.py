"""Login page — v2.4.0: stores refresh_token and session_id on successful login."""

import streamlit as st

from frontend.api.auth import login
from frontend.api.client import APIError
from frontend.utils.constants import PAGE_DASHBOARD, PAGE_REGISTER
from frontend.utils.session import set_auth_data, set_current_page


def render():
    """Render the login page."""
    st.title("🔐 Login")
    st.write("Enter your credentials to access your workspace.")
    
    with st.form("login_form"):
        email = st.text_input("Email", placeholder="you@example.com")
        password = st.text_input("Password", type="password", placeholder="••••••••")
        submitted = st.form_submit_button("Login", use_container_width=True)
        
        if submitted:
            if not email or not password:
                st.error("Please fill in all fields.")
                return
            
            try:
                with st.spinner("Logging in..."):
                    response = login(email, password)
                    
                    # Store auth data — v2.4.0: includes refresh_token + session_id
                    set_auth_data(
                        access_token=response["access_token"],
                        token_type=response.get("token_type", "bearer"),
                        user_data={"email": email},
                        refresh_token=response.get("refresh_token"),
                        session_id=str(response["session_id"]) if response.get("session_id") else None,
                    )
                    
                    st.success("Login successful!")
                    set_current_page(PAGE_DASHBOARD)
                    st.rerun()
                    
            except APIError as e:
                st.error(f"Login failed: {e.message}")
    
    st.divider()
    st.write("Don't have an account?")
    if st.button("Create Account", use_container_width=True):
        set_current_page(PAGE_REGISTER)
        st.rerun()
