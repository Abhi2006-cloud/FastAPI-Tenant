"""Register page."""

import streamlit as st

from frontend.api.auth import register
from frontend.api.client import APIError
from frontend.utils.constants import PAGE_LOGIN
from frontend.utils.session import set_current_page


def render():
    """Render the register page."""
    st.title("📝 Create Account")
    st.write("Join AI Workspace and start collaborating.")
    
    with st.form("register_form"):
        email = st.text_input("Email", placeholder="you@example.com")
        password = st.text_input("Password", type="password", placeholder="••••••••")
        confirm_password = st.text_input("Confirm Password", type="password", placeholder="••••••••")
        submitted = st.form_submit_button("Create Account", use_container_width=True)
        
        if submitted:
            if not email or not password or not confirm_password:
                st.error("Please fill in all fields.")
                return
            
            if password != confirm_password:
                st.error("Passwords do not match.")
                return
            
            if len(password) < 8:
                st.error("Password must be at least 8 characters long.")
                return
            
            try:
                with st.spinner("Creating account..."):
                    response = register(email, password)
                    
                    st.success("Account created successfully! Please login.")
                    set_current_page(PAGE_LOGIN)
                    st.rerun()
                    
            except APIError as e:
                st.error(f"Registration failed: {e.message}")
    
    st.divider()
    st.write("Already have an account?")
    if st.button("Login", use_container_width=True):
        set_current_page(PAGE_LOGIN)
        st.rerun()
