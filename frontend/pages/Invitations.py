"""Invitations page."""

import streamlit as st

from frontend.api.client import APIError
from frontend.api.invitations import accept_invitation, create_invitation
from frontend.components.auth_guard import require_auth, require_organization
from frontend.utils.session import get_organization_id


def render():
    """Render the invitations page."""
    require_auth()
    
    st.title("✉️ Invitations")
    
    # Section 1: Create Invitation
    st.subheader("Create Invitation")
    
    if require_organization():
        org_id = get_organization_id()
        
        with st.form("create_invitation_form"):
            invitee_email = st.text_input("Invitee Email", placeholder="colleague@example.com")
            submitted = st.form_submit_button("Send Invitation", use_container_width=True)
            
            if submitted:
                if not invitee_email:
                    st.error("Please enter an email address.")
                    return
                
                try:
                    with st.spinner("Creating invitation..."):
                        invitation = create_invitation(org_id, invitee_email)
                        
                        st.success(f"Invitation created for {invitee_email}!")
                        st.info(f"**Invitation Token:** `{invitation['token']}`")
                        
                        # Copy to clipboard
                        st.code(invitation['token'])
                        st.caption("Share this token with the invitee. They can use it to accept the invitation.")
                        
                except APIError as e:
                    st.error(f"Failed to create invitation: {e.message}")
    
    st.divider()
    
    # Section 2: Accept Invitation
    st.subheader("Accept Invitation")
    
    with st.form("accept_invitation_form"):
        invitation_token = st.text_input("Invitation Token", placeholder="Enter your invitation token")
        submitted = st.form_submit_button("Accept Invitation", use_container_width=True)
        
        if submitted:
            if not invitation_token:
                st.error("Please enter an invitation token.")
                return
            
            try:
                with st.spinner("Accepting invitation..."):
                    invitation = accept_invitation(invitation_token)
                    
                    st.success(f"Invitation accepted! You are now a member of the organization.")
                    st.info(f"**Organization ID:** {invitation['organization_id']}")
                    
                    # Refresh organizations
                    from frontend.api.organizations import list_my_organizations
                    from frontend.utils.session import set_organizations
                    orgs = list_my_organizations()
                    set_organizations(orgs)
                    
                    # Auto-select the organization
                    from frontend.utils.session import set_organization_id
                    set_organization_id(invitation['organization_id'])
                    st.rerun()
                    
            except APIError as e:
                st.error(f"Failed to accept invitation: {e.message}")
