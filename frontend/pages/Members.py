"""Members page for organization member management."""

import streamlit as st

from frontend.api.client import APIError
from frontend.api.memberships import (
    change_member_role,
    list_members,
    remove_member,
    transfer_ownership,
)
from frontend.api.organizations import list_my_organizations
from frontend.components.auth_guard import require_auth
from frontend.utils.session import get_organization_id, get_user


def render():
    """Render the members page."""
    require_auth()
    
    st.title("👥 Organization Members")
    
    organization_id = get_organization_id()
    user = get_user()
    
    if not organization_id:
        st.warning("Please select an organization from the sidebar to manage members.")
        return
    
    # Load members
    try:
        with st.spinner("Loading members..."):
            members = list_members(organization_id)
    except APIError as e:
        st.error(f"Failed to load members: {e.message}")
        return
    
    if not members:
        st.info("No members found in this organization.")
        return
    
    # Find current user's membership and role
    current_user_membership = None
    for member in members:
        if member["user_id"] == user["id"]:
            current_user_membership = member
            break
    
    is_owner = current_user_membership and current_user_membership["role"] == "owner"
    
    # Display members table
    st.subheader("Members")
    
    for member in members:
        with st.expander(
            f"{'👑' if member['role'] == 'owner' else '🛡️' if member['role'] == 'admin' else '👤'} "
            f"{member['email']} ({member['role'].capitalize()})"
        ):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.write(f"**Email:** {member['email']}")
            
            with col2:
                st.write(f"**Role:** {member['role'].capitalize()}")
            
            with col3:
                st.write(f"**Joined:** {member['created_at'][:10]}")
            
            # Show management actions only for owner
            if is_owner:
                st.divider()
                
                # Cannot manage owner role
                if member["role"] == "owner":
                    st.info("Owner role cannot be modified directly. Use 'Transfer Ownership' to change owner.")
                
                # Can manage admin and member roles
                elif member["role"] in ["admin", "member"]:
                    action_col1, action_col2, action_col3 = st.columns(3)
                    
                    with action_col1:
                        if member["role"] == "member":
                            if st.button(
                                "Promote to Admin",
                                key=f"promote_{member['membership_id']}",
                                use_container_width=True,
                            ):
                                try:
                                    with st.spinner("Updating role..."):
                                        change_member_role(
                                            organization_id,
                                            member["membership_id"],
                                            "admin",
                                        )
                                        st.success(f"Promoted {member['email']} to admin")
                                        st.rerun()
                                except APIError as e:
                                    st.error(f"Failed to promote member: {e.message}")
                    
                    with action_col2:
                        if member["role"] == "admin":
                            if st.button(
                                "Demote to Member",
                                key=f"demote_{member['membership_id']}",
                                use_container_width=True,
                            ):
                                try:
                                    with st.spinner("Updating role..."):
                                        change_member_role(
                                            organization_id,
                                            member["membership_id"],
                                            "member",
                                        )
                                        st.success(f"Demoted {member['email']} to member")
                                        st.rerun()
                                except APIError as e:
                                    st.error(f"Failed to demote admin: {e.message}")
                    
                    with action_col3:
                        if st.button(
                            "Remove Member",
                            key=f"remove_{member['membership_id']}",
                            use_container_width=True,
                        ):
                            try:
                                with st.spinner("Removing member..."):
                                    remove_member(organization_id, member["membership_id"])
                                    st.success(f"Removed {member['email']} from organization")
                                    st.rerun()
                            except APIError as e:
                                st.error(f"Failed to remove member: {e.message}")
    
    st.divider()
    
    # Transfer Ownership section (owner only)
    if is_owner and len(members) > 1:
        st.subheader("👑 Transfer Ownership")
        st.warning("⚠️ You will lose owner privileges after transferring ownership.")
        
        # Get non-owner members
        transfer_candidates = [m for m in members if m["role"] != "owner"]
        
        if transfer_candidates:
            selected_member = st.selectbox(
                "Select new owner",
                options=transfer_candidates,
                format_func=lambda m: f"{m['email']} ({m['role'].capitalize()})",
                key="transfer_owner_select",
            )
            
            if st.button(
                "Transfer Ownership",
                use_container_width=True,
                type="primary",
            ):
                if st.session_state.get("confirm_transfer", False):
                    try:
                        with st.spinner("Transferring ownership..."):
                            transfer_ownership(
                                organization_id,
                                selected_member["membership_id"],
                            )
                            st.success(f"Ownership transferred to {selected_member['email']}")
                            st.session_state["confirm_transfer"] = False
                            st.rerun()
                    except APIError as e:
                        st.error(f"Failed to transfer ownership: {e.message}")
                        st.session_state["confirm_transfer"] = False
                else:
                    st.session_state["confirm_transfer"] = True
                    st.warning(
                        f"Are you sure you want to transfer ownership to {selected_member['email']}? "
                        "Click the button again to confirm."
                    )
        else:
            st.info("No other members available to transfer ownership to.")
    elif is_owner:
        st.info("You need at least one other member in the organization to transfer ownership.")
