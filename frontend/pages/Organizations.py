"""Organizations page."""

import streamlit as st

from frontend.api.client import APIError
from frontend.api.organizations import create_organization, list_my_organizations
from frontend.components.auth_guard import require_auth
from frontend.utils.session import get_organizations, set_organization_id, set_organizations


def render():
    """Render the organizations page."""
    require_auth()
    
    st.title("🏢 Organizations")
    
    # Section 1: Create Organization
    st.subheader("Create New Organization")
    
    with st.form("create_org_form"):
        org_name = st.text_input("Organization Name", placeholder="My Workspace")
        submitted = st.form_submit_button("Create Organization", use_container_width=True)
        
        if submitted:
            if not org_name:
                st.error("Please enter an organization name.")
                return
            
            try:
                with st.spinner("Creating organization..."):
                    new_org = create_organization(org_name)
                    
                    st.success(f"Organization '{new_org['name']}' created successfully!")
                    
                    # Refresh organizations list
                    orgs = list_my_organizations()
                    set_organizations(orgs)
                    
                    # Auto-select the new organization
                    set_organization_id(new_org['id'])
                    st.rerun()
                    
            except APIError as e:
                st.error(f"Failed to create organization: {e.message}")
    
    st.divider()
    
    # Section 2: My Organizations
    st.subheader("My Organizations")
    
    organizations = get_organizations()
    
    if not organizations:
        try:
            with st.spinner("Loading organizations..."):
                orgs = list_my_organizations()
                set_organizations(orgs)
                organizations = orgs
        except APIError as e:
            st.error(f"Failed to load organizations: {e.message}")
    
    if organizations:
        for org in organizations:
            with st.expander(f"🏢 {org['name']}"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**ID:** {org['id']}")
                    st.write(f"**Owner ID:** {org['owner_id']}")
                
                with col2:
                    st.write(f"**Created:** {org['created_at']}")
                
                # Select as active organization
                from frontend.utils.session import get_organization_id
                current_org_id = get_organization_id()
                
                if org['id'] != current_org_id:
                    if st.button(f"Select {org['name']}", key=f"select_{org['id']}", use_container_width=True):
                        set_organization_id(org['id'])
                        st.success(f"Selected '{org['name']}' as active organization")
                        st.rerun()
                else:
                    st.success("✅ Currently selected")
    else:
        st.info("You don't have any organizations yet. Create one above!")
