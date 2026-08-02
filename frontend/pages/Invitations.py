"""Invitations page with link-based auto-acceptance."""

import streamlit as st

from frontend.api.client import APIError
from frontend.api.invitations import accept_invitation, create_invitation
from frontend.components.auth_guard import require_auth, require_organization
from frontend.utils.session import get_organization_id, is_authenticated


def render():
    """Render the invitations page."""
    # Check for token in URL query params or session state
    query_token = st.query_params.get("token") or st.session_state.get("pending_invitation_token")

    if not is_authenticated():
        if query_token:
            st.session_state["pending_invitation_token"] = query_token
            st.warning("⚠️ You've clicked an invitation link! Please Log In or Register to join the workspace.")
        require_auth()
        return

    st.title("✉️ Invitations")

    # Handle automatic acceptance if a token is present in URL or session state
    if query_token:
        st.info("🚀 Processing invitation token from link...")
        try:
            with st.spinner("Accepting invitation automatically..."):
                invitation = accept_invitation(query_token)
                st.success("🎉 Invitation accepted! You are now a member of the workspace.")

                # Refresh user's organizations
                from frontend.api.organizations import list_my_organizations
                from frontend.utils.session import set_organization_id, set_organizations
                orgs = list_my_organizations()
                set_organizations(orgs)
                set_organization_id(invitation["organization_id"])

                # Clean up query params and session state
                if "token" in st.query_params:
                    del st.query_params["token"]
                if "pending_invitation_token" in st.session_state:
                    del st.session_state["pending_invitation_token"]

                st.balloons()
                st.rerun()
        except APIError as e:
            st.error(f"Failed to accept invitation: {e.message}")
            if "token" in st.query_params:
                del st.query_params["token"]
            if "pending_invitation_token" in st.session_state:
                del st.session_state["pending_invitation_token"]

    # Section 1: Create Invitation
    st.subheader("Invite Workspace Member")

    if require_organization():
        org_id = get_organization_id()

        with st.form("create_invitation_form"):
            invitee_email = st.text_input("Invitee Email Address", placeholder="colleague@example.com")
            submitted = st.form_submit_button("Send Invitation Email", use_container_width=True)

            if submitted:
                if not invitee_email:
                    st.error("Please enter an email address.")
                    return

                try:
                    with st.spinner("Processing invitation..."):
                        invitation = create_invitation(org_id, invitee_email)

                        delivery_mode = invitation.get("delivery_mode", "development")
                        delivery_status = invitation.get("delivery_status", "manual_sharing_required")
                        join_url = invitation.get("invitation_url") or f"http://localhost:8501/invitations?token={invitation.get('token', '')}"

                        if delivery_mode == "production" and delivery_status == "email_sent":
                            st.success(f"Invitation email queued successfully for {invitee_email}!")
                            st.info("The invitee will receive an email containing a secure 'Join Workspace' link.")
                        else:
                            st.success(f"Invitation created for {invitee_email}!")
                            st.info(
                                "ℹ️ **Email delivery is currently running in Development Mode.** "
                                "Invitations are generated successfully, but emails cannot be sent until a verified email domain is configured."
                            )
                            st.markdown("**Copy & Share Invitation Link:**")
                            st.text_input(
                                "Invitation Link",
                                value=join_url,
                                key="copyable_invitation_url",
                                help="Copy this link and share it directly with the invitee to join the workspace.",
                            )

                            if invitation.get("token"):
                                st.caption(f"Invitation Token: `{invitation['token']}`")

                except APIError as e:
                    st.error(f"Failed to create invitation: {e.message}")

    st.divider()

    # Section 2: Accept Invitation Manually
    st.subheader("Manual Invitation Token Acceptance")

    with st.form("accept_invitation_form"):
        invitation_token = st.text_input(
            "Invitation Token",
            value=query_token or "",
            placeholder="Enter invitation token (if accepting manually)",
        )
        submitted = st.form_submit_button("Accept Invitation", use_container_width=True)

        if submitted:
            if not invitation_token:
                st.error("Please enter an invitation token.")
                return

            try:
                with st.spinner("Accepting invitation..."):
                    invitation = accept_invitation(invitation_token)

                    st.success("Invitation accepted! You are now a member of the organization.")
                    st.info(f"**Organization ID:** {invitation['organization_id']}")

                    from frontend.api.organizations import list_my_organizations
                    from frontend.utils.session import set_organization_id, set_organizations
                    orgs = list_my_organizations()
                    set_organizations(orgs)
                    set_organization_id(invitation["organization_id"])
                    st.rerun()

            except APIError as e:
                st.error(f"Failed to accept invitation: {e.message}")
