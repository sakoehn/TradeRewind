"""Shared UI for all files logo, custom CSS, layout."""

import os
from typing import Optional

import streamlit as st

# Logo path relative to project root (where Streamlit is run)
LOGO_PATH = ".streamlit/logo.png"

# Custom CSS
CUSTOM_CSS = """
<style>
    /* Main content: full width, comfortable padding */
    .main .block-container {
        max-width: 100%;
        padding-left: 2rem;
        padding-right: 2rem;
        padding-top: 1rem;
        padding-bottom: 2rem;
    }
    /* Logo */
    div[data-testid="stImage"] img {
        max-height: 150px;
        width: auto;
        object-fit: contain;
    }
    /* Headers: soft emerald for a friendly look */
    h1, h2, h3 {
        color: #047857 !important;
        font-weight: 600;
    }
    /* Caption / subtitle a bit softer */
    .stCaption {
        color: #64748b !important;
    }
    /* Cards and blocks: subtle elevation */
    [data-testid="stVerticalBlock"] > div {
        border-radius: 10px;
    }
    .stAlert {
        border-radius: 10px;
        border-left: 4px solid #059669;
    }
    /* Primary buttons: emerald, rounded */
    .stButton > button[kind="primary"] {
        background-color: #059669;
        color: #ffffff;
        border: none;
        font-weight: 600;
        border-radius: 8px;
        padding: 0.5rem 1.25rem;
    }
    .stButton > button[kind="primary"]:hover {
        background-color: #047857;
        color: #ffffff;
    }
    /* Secondary buttons: outline style */
    .stButton > button[kind="secondary"] {
        background-color: #ffffff;
        color: #059669;
        border: 1px solid #059669;
        border-radius: 8px;
    }
    .stButton > button[kind="secondary"]:hover {
        background-color: #f0fdf4;
        color: #047857;
        border-color: #047857;
    }
    /* Sidebar: clean light */
    [data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #e2e8f0;
    }
    [data-testid="stSidebar"] .stMarkdown {
        color: #334155;
    }
    [data-testid="stSidebar"] [data-testid="stMarkdown"] a {
        color: #059669;
    }
    /* Inputs: subtle focus ring */
    .stSelectbox, .stTextInput, .stNumberInput {
        border-radius: 8px;
    }
</style>
"""


def inject_custom_style() -> None:
    """Inject custom CSS for layout and light, modern theme."""
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def render_logo(logo_path: Optional[str] = None) -> None:
    """Show the app logo above the page content. Call once at top of each page."""
    path = logo_path or LOGO_PATH
    if not os.path.isfile(path):
        return
    _, col2, _ = st.columns([1, 2, 1])
    with col2:
        st.image(path, use_container_width=True)
    st.write("")


def apply_shared_ui(logo_path: Optional[str] = None) -> None:
    """Apply custom CSS and render logo. Call at the start of each page."""
    inject_custom_style()
    render_logo(logo_path)
