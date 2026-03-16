"""TradeRewind Streamlit app launcher."""

import streamlit as st

st.set_page_config(
    page_title="Trade Rewind",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

pg = st.navigation([
    st.Page("home_page.py", title="Home Page"),
    st.Page("pages/stocks_info.py", title="Stock Information"),
    st.Page("pages/compare_tickers.py", title="Compare Tickers"),
    st.Page("pages/backtester_info.py", title="Strategy Information"),
])
pg.run()