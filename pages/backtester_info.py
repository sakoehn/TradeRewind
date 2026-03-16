"""Strategy information page for TradeRewind."""

import streamlit as st

from ui_shared import apply_shared_ui

apply_shared_ui()

st.title("Strategy Information Page")
st.set_page_config(page_title="Strategy Information")  

if st.button("Back to main page", type="secondary"):
    st.switch_page("home_page.py")
