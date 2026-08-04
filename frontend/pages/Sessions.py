"""
Sessions Management Page — v2.4.0

Displays all active login sessions for the current user.
Features:
  - Current device highlighted with a badge
  - Device/browser/platform/IP/timestamps shown per row
  - Revoke individual sessions remotely
  - Logout All Devices button
  - Manual token refresh
"""

from datetime import datetime, timezone

import streamlit as st

from frontend.api.auth import get_sessions, logout_all, revoke_session, refresh_token
from frontend.api.client import APIError
from frontend.components.auth_guard import require_auth
from frontend.utils.session import (
    clear_auth_data,
    get_refresh_token,
    get_session_id,
    set_current_page,
    update_tokens,
)
from frontend.utils.constants import PAGE_LOGIN


def _format_relative_time(dt_str: str) -> str:
    """Convert ISO datetime string to human-readable relative time."""
    try:
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        delta = now - dt
        seconds = int(delta.total_seconds())
        if seconds < 60:
            return f"{seconds}s ago"
        elif seconds < 3600:
            return f"{seconds // 60}m ago"
        elif seconds < 86400:
            return f"{seconds // 3600}h ago"
        elif seconds < 604800:
            return f"{seconds // 86400}d ago"
        else:
            return dt.strftime("%b %d, %Y")
    except Exception:
        return dt_str


def render():
    """Render the Sessions management page."""
    require_auth()

    st.title("🔐 Active Sessions")
    st.write("Manage all devices where you're currently logged in.")

    current_refresh = get_refresh_token()
    current_session_id = get_session_id()

    # ── Action buttons ────────────────────────────────────────────────────────
    col1, col2, col3 = st.columns([2, 2, 3])

    with col1:
        if st.button("🔄 Refresh List", use_container_width=True):
            st.rerun()

    with col2:
        if st.button("🔁 Rotate My Token", use_container_width=True, help="Manually rotate your refresh token for security"):
            if current_refresh:
                try:
                    with st.spinner("Rotating token..."):
                        result = refresh_token(current_refresh)
                        update_tokens(
                            access_token=result["access_token"],
                            refresh_token=result["refresh_token"],
                            session_id=str(result.get("session_id", "")),
                        )
                    st.success("✅ Token rotated successfully!")
                    st.rerun()
                except APIError as e:
                    st.error(f"Failed to rotate token: {e.message}")
            else:
                st.warning("No refresh token found in session.")

    with col3:
        with st.expander("⚠️ Logout All Devices", expanded=False):
            keep_current = st.checkbox("Keep current session", value=True)
            if st.button("🚫 Confirm Logout All", type="primary", use_container_width=True):
                try:
                    with st.spinner("Revoking all sessions..."):
                        result = logout_all(
                            current_refresh_token=current_refresh,
                            keep_current=keep_current,
                        )
                    revoked_count = result.get("revoked", 0)
                    if not keep_current:
                        st.success(f"All {revoked_count} sessions revoked. You'll need to log in again.")
                        clear_auth_data()
                        set_current_page(PAGE_LOGIN)
                        st.rerun()
                    else:
                        st.success(f"✅ {revoked_count} other session(s) revoked. Your current session is active.")
                        st.rerun()
                except APIError as e:
                    st.error(f"Failed to logout all: {e.message}")

    st.divider()

    # ── Load sessions ─────────────────────────────────────────────────────────
    try:
        with st.spinner("Loading sessions..."):
            data = get_sessions(current_session_id=current_session_id)
            sessions = data.get("sessions", [])
            total = data.get("total", len(sessions))
    except APIError as e:
        st.error(f"Failed to load sessions: {e.message}")
        return

    if not sessions:
        st.info("No active sessions found.")
        return

    st.subheader(f"Active Sessions ({total})")

    # ── Session cards ─────────────────────────────────────────────────────────
    for session in sessions:
        session_id = session.get("id", "")
        is_current = session.get("is_current", False)
        device_name = session.get("device_name") or "Unknown Device"
        browser = session.get("browser") or "Unknown Browser"
        platform = session.get("platform") or "Unknown OS"
        ip_address = session.get("ip_address") or "—"
        created_at = session.get("created_at", "")
        last_used_at = session.get("last_used_at", "")
        expires_at = session.get("expires_at", "")

        # Card container with border styling
        border_color = "#4f46e5" if is_current else "#e5e7eb"
        bg_color = "#f5f3ff" if is_current else "#ffffff"

        with st.container():
            st.markdown(
                f"""
                <div style="
                    border: 2px solid {border_color};
                    border-radius: 12px;
                    padding: 16px 20px;
                    margin-bottom: 12px;
                    background: {bg_color};
                    position: relative;
                ">
                """,
                unsafe_allow_html=True,
            )

            header_col, badge_col = st.columns([4, 1])
            with header_col:
                device_icon = "💻" if "PC" in str(device_name) or "Desktop" in str(device_name) else ("📱" if "Mobile" in str(device_name) else "🖥️")
                label = f"{device_icon} **{device_name}**"
                if is_current:
                    label += " 🟢 **Current**"
                st.markdown(label)

            # Session detail grid
            detail_cols = st.columns(4)
            with detail_cols[0]:
                st.markdown(f"**Browser**\n\n{browser}")
            with detail_cols[1]:
                st.markdown(f"**OS**\n\n{platform}")
            with detail_cols[2]:
                st.markdown(f"**IP Address**\n\n`{ip_address}`")
            with detail_cols[3]:
                last_active = _format_relative_time(last_used_at) if last_used_at else "—"
                st.markdown(f"**Last Active**\n\n{last_active}")

            # Timestamps row
            ts_cols = st.columns(2)
            with ts_cols[0]:
                created_display = _format_relative_time(created_at) if created_at else "—"
                st.caption(f"🕐 Created: {created_display}")
            with ts_cols[1]:
                expires_display = _format_relative_time(expires_at) if expires_at else "—"
                st.caption(f"⏳ Expires: {expires_display}")

            # Revoke button (disabled for current session)
            if not is_current:
                if st.button(
                    "🚫 Logout This Device",
                    key=f"revoke_{session_id}",
                    type="secondary",
                    help=f"Revoke session {session_id[:8]}...",
                ):
                    try:
                        revoke_session(session_id)
                        st.success(f"✅ Session for {device_name} has been revoked.")
                        st.rerun()
                    except APIError as e:
                        st.error(f"Failed to revoke: {e.message}")
            else:
                st.caption("*This is your current session — use 'Logout All' to revoke it.*")

            st.markdown("</div>", unsafe_allow_html=True)

    # ── Security tip ──────────────────────────────────────────────────────────
    st.divider()
    st.info(
        "💡 **Security Tip**: If you see a session you don't recognise, "
        "immediately revoke it and change your password. "
        "Your access token expires every 15 minutes automatically."
    )
