"""Stock information page for TradeRewind."""

import streamlit as st

from data_loading import load_all_data
from ui_shared import apply_shared_ui

apply_shared_ui()

st.title("Stock Information Page")
st.caption("Browse and search the stocks available in Trade Rewind.")

if st.button("Back to main page", type="secondary"):
    st.switch_page("home_page.py")

st.write("")

stocks_df = load_all_data()
unique_pairs = (
    stocks_df[["ticker", "company_name"]]
    .drop_duplicates()
    .sort_values("ticker")
)

options = [
    f"{row['ticker']}: {row['company_name']}"
    for _, row in unique_pairs.iterrows()
]

st.write("### Search and select a ticker")
selected_label = st.selectbox(
    "Start typing a ticker or company name, then pick from the list.",
    options=options,
    index=0 if options else None,
)

if selected_label:
    st.success(f"You selected: {selected_label}")

st.write("")
st.write("### All tickers")

N_COLS = 6
cols = st.columns(N_COLS)
per_col = (len(options) + N_COLS - 1) // N_COLS

for col_idx, col in enumerate(cols):
    start = col_idx * per_col
    end = start + per_col
    with col:
        for text in options[start:end]:
            st.markdown(text)
