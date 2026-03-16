"""Strategy information page for TradeRewind."""

import streamlit as st

from ui_shared import apply_shared_ui

apply_shared_ui()

st.title("Strategy Information Page")

if st.button("Back to main page", type="secondary"):
    st.switch_page("home_page.py")

st.write("")

# ── Buy and Hold ─────────────────────────────────────────────────────────────
st.subheader("Buy and Hold")
st.write(
    "The simplest possible strategy. On day one the entire starting capital "
    "is used to purchase shares of the selected stock, and those shares are "
    "held for the entire backtest period with no further trading."
)
st.write("**Configurable attributes:**")
st.markdown(
    "- **Ticker** — the stock to buy.\n"
    "- **Start / End date** — the date range for the backtest.\n"
    "- **Starting capital** — the dollar amount invested on day one."
)

st.divider()

# ── Moving Average Crossover ─────────────────────────────────────────────────
st.subheader("Moving Average Crossover")
st.write(
    "A trend-following strategy that uses two Simple Moving Averages (SMA). "
    "When the short-term SMA (50-day) crosses above the long-term SMA "
    "(200-day) — a *Golden Cross* — the strategy buys. When the short-term "
    "SMA crosses below the long-term SMA — a *Death Cross* — the strategy "
    "sells. This aims to capture sustained trends while filtering out "
    "short-term noise."
)
st.write("**Configurable attributes:**")
st.markdown(
    "- **Ticker** — the stock to trade.\n"
    "- **Start / End date** — the date range for the backtest. "
    "Requires at least 201 trading days (~1 year) of data.\n"
    "- **Starting capital** — the dollar amount available for trading."
)
st.info(
    "The 50-day and 200-day window sizes are fixed. "
    "All capital is invested on a buy signal and fully liquidated on a sell signal.",
    icon="ℹ️",
)

st.divider()

# ── Momentum ─────────────────────────────────────────────────────────────────
st.subheader("Momentum")
st.write(
    "A momentum strategy that compares today's closing price to the closing "
    "price *N* days ago (the lookback period). If the ratio is greater than 1 "
    "(price is rising), the strategy buys a fixed percentage of the initial "
    "capital. If the ratio is less than 1 (price is falling), it sells that "
    "same percentage. This allows gradual position building during uptrends "
    "and gradual unwinding during downtrends."
)
st.write("**Configurable attributes:**")
st.markdown(
    "- **Ticker** — the stock to trade.\n"
    "- **Start / End date** — the date range for the backtest.\n"
    "- **Starting capital** — the dollar amount available for trading.\n"
    "- **Lookback days** *(1–100, default 20)* — how many trading days back "
    "to compare the current price against. A shorter lookback reacts faster "
    "to price changes; a longer lookback smooths out noise.\n"
    "- **Trade proportion** *(1%–100%, default 10%)* — the percentage of "
    "initial capital to buy or sell on each signal. A smaller proportion "
    "builds positions gradually; a larger proportion is more aggressive."
)
