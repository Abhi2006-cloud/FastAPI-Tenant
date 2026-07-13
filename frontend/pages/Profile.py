"""Profile page."""

import streamlit as st

from frontend.api.auth import get_me
from frontend.api.client import APIError
from frontend.components.auth_guard import require_auth


def render():
    """Render the profile page."""
    require_auth()
    
    st.title("👤 Profile")
    
    try:
        with st.spinner("Loading profile..."):
            user_data = get_me()
            
            # Update session state with fresh data
            st.session_state.user = user_data
            
            # Display user information
            st.subheader("User Information")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric("User ID", str(user_data['id']))
                st.metric("Email", user_data['email'])
            
            with col2:
                st.metric("Created At", user_data['created_at'])
            
            st.divider()
            
            # Additional details
            st.subheader("Account Details")
            
            with st.expander("Full User Data"):
                st.json(user_data)
                
    except APIError as e:
        st.error(f"Failed to load profile: {e.message}")
