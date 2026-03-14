"""Stock information page for TradeRewind."""

import streamlit as st
from data_loading import load_all_data

st.title("Stock Information Page")
st.caption("Browse the stocks available in Trade Rewind.")

if st.button("Back to main page", type="secondary"):
    st.switch_page("home_page.py")

st.write("")
st.write("### ticker : company name ")

stocks_df = load_all_data()

pairs = (
    stocks_df[["ticker", "company_name"]]
    .drop_duplicates()
    .sort_values("ticker")
    .apply(lambda row: f"{row['ticker']}: {row['company_name']}", axis=1)
    .tolist()
)

N_COLS = 6
cols = st.columns(N_COLS)

per_col = (len(pairs) + N_COLS - 1) // N_COLS

for col_idx, col in enumerate(cols):
    start = col_idx * per_col
    end = start + per_col
    with col:
        for text in pairs[start:end]:
            st.markdown(text)
