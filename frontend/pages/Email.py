"""Streamlit Email Infrastructure & Operational Dashboard page."""

import streamlit as st

from frontend.api.client import APIError
from frontend.api.email import (
    get_email_stats,
    list_email_logs,
    retry_email_log,
    send_test_email,
)
from frontend.components.auth_guard import require_auth
from frontend.utils.session import get_organization_id


def render():
    """Render the Email Management & Infrastructure Dashboard."""
    require_auth()

    st.title("📧 Email Infrastructure & Operations")
    st.caption("Monitor background email delivery, inspect email audit logs, and test providers.")

    org_id = get_organization_id()

    # Section 1: Provider Status & Delivery Stats
    try:
        stats = get_email_stats(org_id)
        health = stats.get("health_status", {})
        active_provider = stats.get("active_provider", "console").upper()
        health_status = health.get("status", "unknown").upper()
        email_mode = health.get("email_mode", "development").upper()

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Delivery Mode", email_mode)
        with col2:
            st.metric("Provider Health", health_status)
        with col3:
            st.metric("Total Emails", stats.get("total_emails", 0))
        with col4:
            st.metric("Success Rate", f"{stats.get('success_rate_percent', 100.0)}%")

        if email_mode == "DEVELOPMENT":
            st.info(
                "ℹ️ **Development Mode Active**: Email delivery runs in fallback mode. "
                "Invitations generate tokens and links cleanly so developers can test locally without external domain infrastructure."
            )

        st.divider()

    except APIError as e:
        st.error(f"Failed to fetch email statistics: {e.message}")

    # Tabs layout
    tab_logs, tab_test, tab_templates = st.tabs(["📋 Email Audit Logs", "🧪 Send Test Email", "📄 Template Library"])

    with tab_logs:
        st.subheader("Email Audit History")

        col_filter1, col_filter2 = st.columns(2)
        with col_filter1:
            status_filter = st.selectbox(
                "Filter by Status",
                ["ALL", "QUEUED", "PROCESSING", "SENT", "FAILED", "CANCELLED"],
            )
        with col_filter2:
            recipient_filter = st.text_input("Filter by Recipient Email", placeholder="user@example.com")

        try:
            status_param = None if status_filter == "ALL" else status_filter
            logs_data = list_email_logs(
                org_id=org_id,
                status=status_param,
                recipient=recipient_filter or None,
                limit=50,
            )
            logs = logs_data.get("logs", [])
            total = logs_data.get("total", 0)

            st.caption(f"Showing {len(logs)} of {total} email logs")

            if not logs:
                st.info("No email logs found matching the selected criteria.")
            else:
                for log in logs:
                    with st.expander(
                        f"[{log['status']}] {log['subject']} ➔ {log['recipient_email']} ({log['created_at'][:19]})"
                    ):
                        st.markdown(f"**Log ID:** `{log['id']}`")
                        st.markdown(f"**Provider:** `{log['provider']}` | **Template:** `{log['template_name']}`")
                        st.markdown(f"**RQ Job ID:** `{log.get('rq_job_id') or 'N/A'}`")
                        st.markdown(f"**Retries:** `{log.get('retry_count', 0)}`")

                        if log.get("sent_at"):
                            st.success(f"Sent At: {log['sent_at'][:19]} (Message ID: {log.get('provider_message_id')})")
                        if log.get("error_message"):
                            st.error(f"Error: {log['error_message']}")

                        if log["status"] in ("FAILED", "CANCELLED"):
                            if st.button(f"🔄 Retry Email Delivery", key=f"retry_{log['id']}"):
                                try:
                                    retry_email_log(log["id"])
                                    st.success(f"Re-queued email log {log['id']} for retry!")
                                    st.rerun()
                                except APIError as err:
                                    st.error(f"Failed to retry: {err.message}")

        except APIError as e:
            st.error(f"Failed to load email logs: {e.message}")

    with tab_test:
        st.subheader("Send Test Email")
        with st.form("test_email_form"):
            recipient = st.text_input("Recipient Email", placeholder="user@example.com")
            subject = st.text_input("Subject Line", value="Test Email from AI Workspace")
            template = st.selectbox(
                "Select Template",
                ["welcome.html", "invitation.html", "password_reset.html", "email_verification.html"],
            )
            submitted = st.form_submit_button("Send Test Email", use_container_width=True)

            if submitted:
                if not recipient:
                    st.error("Please enter a recipient email.")
                else:
                    try:
                        res = send_test_email(to_email=recipient, subject=subject, template_name=template)
                        st.success(f"Test email queued successfully! (Log ID: {res['id']})")
                    except APIError as e:
                        st.error(f"Failed to send test email: {e.message}")

    with tab_templates:
        st.subheader("Registered Email Templates")
        templates_info = [
            {"Name": "invitation.html", "Category": "Invitations", "Description": "Workspace invitation link with Join Workspace button."},
            {"Name": "welcome.html", "Category": "Onboarding", "Description": "Welcome email sent upon user registration."},
            {"Name": "password_reset.html", "Category": "Security", "Description": "Password reset link for account recovery."},
            {"Name": "email_verification.html", "Category": "Security", "Description": "Email verification link for new user accounts."},
        ]
        st.table(templates_info)
