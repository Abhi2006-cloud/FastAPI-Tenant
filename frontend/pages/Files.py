"""Files page."""

import streamlit as st
import pandas as pd

from frontend.api.client import APIError
from frontend.api.files import delete_file, download_file, get_file_statistics, list_files, upload_file
from frontend.api.memberships import list_members
from frontend.components.auth_guard import require_auth, require_organization
from frontend.utils.session import get_organization_id, get_user


def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    if size_bytes == 0:
        return "0 B"
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


def render():
    """Render the files page."""
    require_auth()
    
    st.title("📁 Files")
    
    # Check organization selection
    if not require_organization():
        return
    
    org_id = get_organization_id()
    user = get_user()
    
    # Get user's role for permission-based UI
    user_role = "member"
    try:
        members = list_members(org_id)
        for member in members:
            if member['user_id'] == user['id']:
                user_role = member['role']
                break
    except APIError:
        pass
    
    # Section 1: File Statistics
    st.subheader("Storage Statistics")
    try:
        with st.spinner("Loading statistics..."):
            stats = get_file_statistics()
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Files", stats['total_files'])
            with col2:
                st.metric("Total Storage", format_file_size(stats['total_size_bytes']))
            with col3:
                st.metric("Average File Size", format_file_size(stats['average_file_size']))
    except APIError as e:
        st.warning(f"Could not load statistics: {e.message}")
    
    st.divider()
    
    # Section 2: Upload File
    st.subheader("Upload File")
    
    uploaded_file = st.file_uploader(
        "Choose a file",
        type=["txt", "pdf", "png", "jpg", "jpeg", "gif", "csv", "json", "md", "doc", "docx", "xls", "xlsx"],
        help="Supported formats: txt, pdf, png, jpg, jpeg, gif, csv, json, md, doc, docx, xls, xlsx"
    )
    
    if uploaded_file and st.button("Upload", use_container_width=True):
        try:
            with st.spinner("Uploading file..."):
                file_record = upload_file(uploaded_file)
                st.success(f"File '{file_record['file_name']}' uploaded successfully!")
                st.rerun()
        except APIError as e:
            st.error(f"Failed to upload file: {e.message}")
    
    st.divider()
    
    # Section 3: List Files
    st.subheader("Files in Organization")
    
    try:
        with st.spinner("Loading files..."):
            files = list_files()
    except APIError as e:
        st.error(f"Failed to load files: {e.message}")
        return
    
    if files:
        # Prepare data for display
        file_data = []
        for file in files:
            file_data.append({
                "File Name": file['file_name'],
                "Size": format_file_size(file.get('file_size', 0)),
                "Created At": file['created_at'][:19],  # Truncate microseconds
            })
        
        df = pd.DataFrame(file_data)
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        # Show file details with actions
        st.subheader("File Details & Actions")
        for file in files:
            with st.expander(f"📄 {file['file_name']}"):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.write(f"**File ID:** `{file['id']}`")
                    st.write(f"**File Size:** {format_file_size(file.get('file_size', 0))}")
                    st.write(f"**Created At:** {file['created_at'][:19]}")
                    st.write(f"**Uploaded By:** `{file['uploaded_by']}`")
                
                with col2:
                    # Download button
                    if st.button(f"⬇️ Download", key=f"download_{file['id']}", use_container_width=True):
                        try:
                            with st.spinner("Downloading file..."):
                                content = download_file(file['id'])
                                st.download_button(
                                    label="Save File",
                                    data=content,
                                    file_name=file['file_name'],
                                    mime="application/octet-stream",
                                    key=f"save_{file['id']}"
                                )
                        except APIError as e:
                            st.error(f"Failed to download file: {e.message}")
                    
                    # Delete button (permission-based)
                    can_delete = (user_role in ['owner', 'admin']) or (file['uploaded_by'] == user['id'])
                    if can_delete:
                        if st.button(f"🗑️ Delete", key=f"delete_{file['id']}", use_container_width=True, type="secondary"):
                            try:
                                with st.spinner("Deleting file..."):
                                    delete_file(file['id'])
                                    st.success(f"File '{file['file_name']}' deleted successfully!")
                                    st.rerun()
                            except APIError as e:
                                st.error(f"Failed to delete file: {e.message}")
                    else:
                        st.info("You don't have permission to delete this file")
    else:
        st.info("No files uploaded yet. Upload your first file above!")
