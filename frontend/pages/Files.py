"""Files page."""

import streamlit as st
import pandas as pd

from frontend.api.client import APIError
from frontend.api.files import list_files, upload_file
from frontend.components.auth_guard import require_auth, require_organization
from frontend.utils.session import get_organization_id


def render():
    """Render the files page."""
    require_auth()
    
    st.title("📁 Files")
    
    # Check organization selection
    if not require_organization():
        return
    
    org_id = get_organization_id()
    
    # Section 1: Upload File
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
    
    # Section 2: List Files
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
                "Created At": file['created_at'],
                "Uploaded By": file['uploaded_by'],
            })
        
        df = pd.DataFrame(file_data)
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        # Show file details
        st.subheader("File Details")
        for file in files:
            with st.expander(f"📄 {file['file_name']}"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**File ID:** {file['id']}")
                    st.write(f"**File Path:** {file['file_path']}")
                
                with col2:
                    st.write(f"**Created At:** {file['created_at']}")
                    st.write(f"**Uploaded By:** {file['uploaded_by']}")
    else:
        st.info("No files uploaded yet. Upload your first file above!")
