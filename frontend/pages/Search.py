"""Search Dashboard page."""

import streamlit as st
from datetime import datetime

from frontend.api.client import APIError
from frontend.api.health import get_health
from frontend.api.search import (
    global_search,
    search_organizations,
    search_members,
    search_files,
    search_audit_logs,
)
from frontend.components.auth_guard import require_auth, require_organization
from frontend.utils.session import get_organization_id

def format_file_size(size_bytes: int) -> str:
    if size_bytes == 0:
        return "0 B"
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"

def format_timestamp(ts: int | None) -> str:
    if ts is None:
        return "N/A"
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")

def format_html_highlights(text: str) -> str:
    """Format Meilisearch <em> tags into beautiful UI highlights."""
    return text.replace(
        "<em>", 
        '<mark style="background-color: #ffd166; color: #1d1d24; border-radius: 4px; padding: 1px 4px; font-weight: 600;">'
    ).replace("</em>", "</mark>")

def get_highlighted(hit: dict, field_name: str, fallback_value: str = "") -> str:
    """Extract highlighted text if available, else standard field value."""
    formatted = hit.get("_formatted", {})
    val = formatted.get(field_name) or hit.get(field_name)
    if val is None:
        return fallback_value
    return format_html_highlights(str(val))

def render():
    """Render the Search Dashboard."""
    require_auth()
    
    st.title("🔍 Search Dashboard")
    
    # Verify organization selection
    if not require_organization():
        return
        
    org_id = get_organization_id()
    
    # 1. Fetch health to check Meilisearch status
    search_connected = False
    search_health_msg = "Unknown"
    
    try:
        health_data = get_health()
        search_status = health_data.get("search", "unavailable")
        if search_status == "connected":
            search_connected = True
            search_health_msg = "🟢 Connected (Meilisearch Cloud)"
        else:
            search_health_msg = "🔴 Unavailable / Degraded"
    except Exception as e:
        search_health_msg = f"🔴 Connection Error: {str(e)}"
        
    # Render status bar
    st.markdown(f"**Search Engine Status:** {search_health_msg}")
    st.divider()

    # Graceful degradation check
    if not search_connected:
        st.warning("⚠️ Search service is temporarily unavailable. Full-text search and query execution have been disabled. All other SaaS platform functions remain fully operational.")
        st.info("The application automatically operates in degraded mode. Please contact the administrator or check Meilisearch Cloud credentials.")
        return

    # Tabs for different search categories
    tab_global, tab_files, tab_members, tab_audit, tab_org = st.tabs([
        "🌐 Global Search",
        "📁 Files Search",
        "👥 Members Search",
        "📋 Audit Log Search",
        "🏢 Organization Info"
    ])
    
    # Query configuration
    limit = 10
    
    # TAB 1: Global Search
    with tab_global:
        st.subheader("Cross-Resource Unified Search")
        st.caption("Search across files, members, and audit logs inside the active organization simultaneously.")
        
        q_global = st.text_input("Global query...", key="q_global", placeholder="Type keywords...")
        
        if q_global:
            try:
                with st.spinner("Searching..."):
                    res = global_search(q_global, limit=limit)
                    
                files = res.get("files", [])
                members = res.get("members", [])
                audit_logs = res.get("audit_logs", [])
                totals = res.get("totals", {})
                
                st.markdown(f"### Results for *\"{q_global}\"*")
                
                col1, col2, col3 = st.columns(3)
                col1.metric("Matching Files", totals.get("files", 0))
                col2.metric("Matching Members", totals.get("members", 0))
                col3.metric("Matching Audit Logs", totals.get("audit_logs", 0))
                
                # File Hits
                st.write("---")
                st.markdown("#### 📁 File Matches")
                if files:
                    for f in files:
                        hl_name = get_highlighted(f, "file_name")
                        hl_path = get_highlighted(f, "file_path")
                        st.markdown(
                            f"- **Name:** {hl_name} <br> "
                            f"  **Path:** `{hl_path}` | **Size:** {format_file_size(f.get('file_size', 0))} | "
                            f"  **Created:** {format_timestamp(f.get('created_at'))}",
                            unsafe_allow_html=True
                        )
                else:
                    st.info("No matching files found.")
                
                # Member Hits
                st.markdown("#### 👥 Member Matches")
                if members:
                    for m in members:
                        hl_email = get_highlighted(m, "email")
                        hl_role = get_highlighted(m, "role")
                        st.markdown(
                            f"- **Email:** {hl_email} | **Role:** {hl_role.upper()} | "
                            f"  **Joined:** {format_timestamp(m.get('created_at'))}",
                            unsafe_allow_html=True
                        )
                else:
                    st.info("No matching members found.")
                    
                # Audit Hits
                st.markdown("#### 📋 Audit Log Matches")
                if audit_logs:
                    for a in audit_logs:
                        hl_action = get_highlighted(a, "action")
                        hl_res_type = get_highlighted(a, "resource_type")
                        st.markdown(
                            f"- **Action:** {hl_action} | **Resource Type:** {hl_res_type} | "
                            f"  **Timestamp:** {format_timestamp(a.get('created_at'))} <br>"
                            f"  **Metadata:** `{a.get('metadata', {})}`",
                            unsafe_allow_html=True
                        )
                else:
                    st.info("No matching audit logs found.")
                    
            except APIError as e:
                st.error(f"Search API Error: {e.message}")
        else:
            st.info("Enter keywords above to start searching.")

    # TAB 2: Files Search
    with tab_files:
        st.subheader("Search Files")
        
        col_q, col_s = st.columns([3, 1])
        q_files = col_q.text_input("File query...", key="q_files", placeholder="Search by file name or path...")
        sort_files = col_s.selectbox(
            "Sort by date", 
            options=["Relevance", "Newest First", "Oldest First"],
            key="sort_files"
        )
        
        # Build sorting query param
        sort_param = None
        if sort_files == "Newest First":
            sort_param = "created_at:desc"
        elif sort_files == "Oldest First":
            sort_param = "created_at:asc"
            
        page_files = st.number_input("Page", min_value=1, value=1, step=1, key="page_files")
        offset = (page_files - 1) * limit
        
        if q_files or sort_param:
            try:
                with st.spinner("Searching files..."):
                    res = search_files(q_files, limit=limit, offset=offset, sort=sort_param)
                
                hits = res.get("hits", [])
                total = res.get("totalHits", 0)
                
                st.write(f"Showing {len(hits)} of {total} results")
                
                for f in hits:
                    hl_name = get_highlighted(f, "file_name")
                    hl_path = get_highlighted(f, "file_path")
                    with st.expander(f"📄 {f.get('file_name')}", expanded=True):
                        st.markdown(f"**Name:** {hl_name}", unsafe_allow_html=True)
                        st.markdown(f"**Path:** `{hl_path}`", unsafe_allow_html=True)
                        st.write(f"**Size:** {format_file_size(f.get('file_size', 0))}")
                        st.write(f"**Uploaded By (User ID):** {f.get('uploaded_by')}")
                        st.write(f"**Created At:** {format_timestamp(f.get('created_at'))}")
            except APIError as e:
                st.error(f"Search API Error: {e.message}")
        else:
            st.info("Enter keywords or choose sorting to display files.")

    # TAB 3: Members Search
    with tab_members:
        st.subheader("Search Members")
        
        col_qm, col_sm = st.columns([3, 1])
        q_members = col_qm.text_input("Member query...", key="q_members", placeholder="Search by email or role...")
        sort_members = col_sm.selectbox(
            "Sort by join date", 
            options=["Relevance", "Newest First", "Oldest First"],
            key="sort_members"
        )
        
        sort_param = None
        if sort_members == "Newest First":
            sort_param = "created_at:desc"
        elif sort_members == "Oldest First":
            sort_param = "created_at:asc"
            
        page_members = st.number_input("Page", min_value=1, value=1, step=1, key="page_members")
        offset = (page_members - 1) * limit
        
        if q_members or sort_param:
            try:
                with st.spinner("Searching members..."):
                    res = search_members(q_members, limit=limit, offset=offset, sort=sort_param)
                
                hits = res.get("hits", [])
                total = res.get("totalHits", 0)
                
                st.write(f"Showing {len(hits)} of {total} results")
                
                for m in hits:
                    hl_email = get_highlighted(m, "email")
                    hl_role = get_highlighted(m, "role")
                    with st.expander(f"👤 {m.get('email')}", expanded=True):
                        st.markdown(f"**Email:** {hl_email}", unsafe_allow_html=True)
                        st.markdown(f"**Role:** {hl_role.upper()}", unsafe_allow_html=True)
                        st.write(f"**User ID:** {m.get('user_id')}")
                        st.write(f"**Membership ID:** {m.get('id')}")
                        st.write(f"**Joined:** {format_timestamp(m.get('created_at'))}")
            except APIError as e:
                st.error(f"Search API Error: {e.message}")
        else:
            st.info("Enter keywords or choose sorting to display members.")

    # TAB 4: Audit Log Search
    with tab_audit:
        st.subheader("Search Audit Logs")
        
        col_qa, col_sa = st.columns([3, 1])
        q_audit = col_qa.text_input("Audit query...", key="q_audit", placeholder="Search by action, resource, metadata...")
        sort_audit = col_sa.selectbox(
            "Sort by timestamp", 
            options=["Relevance", "Newest First", "Oldest First"],
            index=1,  # Default to Newest First for audits
            key="sort_audit"
        )
        
        sort_param = None
        if sort_audit == "Newest First":
            sort_param = "created_at:desc"
        elif sort_audit == "Oldest First":
            sort_param = "created_at:asc"
            
        page_audit = st.number_input("Page", min_value=1, value=1, step=1, key="page_audit")
        offset = (page_audit - 1) * limit
        
        if q_audit or sort_param:
            try:
                with st.spinner("Searching audit logs..."):
                    res = search_audit_logs(q_audit, limit=limit, offset=offset, sort=sort_param)
                
                hits = res.get("hits", [])
                total = res.get("totalHits", 0)
                
                st.write(f"Showing {len(hits)} of {total} results")
                
                for a in hits:
                    hl_action = get_highlighted(a, "action")
                    hl_res_type = get_highlighted(a, "resource_type")
                    with st.expander(f"📋 {a.get('action').replace('_', ' ').title()}", expanded=True):
                        st.markdown(f"**Action:** {hl_action}", unsafe_allow_html=True)
                        st.markdown(f"**Resource Type:** {hl_res_type}", unsafe_allow_html=True)
                        st.write(f"**Resource ID:** {a.get('resource_id')}")
                        st.write(f"**Actor User ID:** {a.get('actor_user_id') or 'System'}")
                        st.write(f"**Timestamp:** {format_timestamp(a.get('created_at'))}")
                        st.write(f"**Metadata:** `{a.get('metadata')}`")
            except APIError as e:
                st.error(f"Search API Error: {e.message}")
        else:
            st.info("Enter keywords or choose sorting to display audit logs.")

    # TAB 5: Organization Info
    with tab_org:
        st.subheader("Search Organization Details")
        st.caption("Verifies indices and search information for the active organization context.")
        
        q_org = st.text_input("Organization query...", key="q_org", placeholder="Search organization name...")
        
        if q_org:
            try:
                with st.spinner("Searching organization..."):
                    res = search_organizations(q_org, limit=1)
                
                hits = res.get("hits", [])
                if hits:
                    org_data = hits[0]
                    hl_name = get_highlighted(org_data, "name")
                    st.success("Matching Organization Context Found!")
                    st.markdown(f"**Organization ID:** `{org_data.get('id')}`")
                    st.markdown(f"**Highlighted Name:** {hl_name}", unsafe_allow_html=True)
                    st.markdown(f"**Owner User ID:** `{org_data.get('owner_id')}`")
                    st.markdown(f"**Created At:** {format_timestamp(org_data.get('created_at'))}")
                else:
                    st.warning("No matching organization found for query in current tenant context.")
            except APIError as e:
                st.error(f"Search API Error: {e.message}")
        else:
            st.info("Type keywords to verify organization indexing metadata.")
