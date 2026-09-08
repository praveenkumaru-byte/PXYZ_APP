import streamlit as st
from github import Github

def push_to_github(file_path, commit_message, content_data):
    """Pushes string (CSV) or byte (Images/PDFs) data directly to the GitHub repo."""
    try:
        g = Github(st.secrets["GITHUB_TOKEN"])
        repo = g.get_repo("praveenkumaru-byte/PXYZ_APP")
        
        try:
            # Update file if it already exists
            contents = repo.get_contents(file_path)
            repo.update_file(contents.path, commit_message, content_data, contents.sha)
        except:
            # Create file if it does not exist
            repo.create_file(file_path, commit_message, content_data)
    except Exception as e:
        st.error(f"⚠️ GitHub Sync Failed: {e}")