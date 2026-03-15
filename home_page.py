"""Streamlit home page for TradeRewind.

Provides the main UI for configuring and running a backtest.
This file is the Streamlit main script so the sidebar shows only Home + pages.
"""

import streamlit as st
import pandas as pd

from backtester import InvalidTickerError, main_backtest
from data_loading import load_all_data
from strategies import (
    display_name_to_key,
    get_strategy_display_names,
    STRATEGY_INFO,
)
from ui_shared import apply_shared_ui

st.set_page_config(
    page_title="Trade Rewind",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)
apply_shared_ui()


def _available_tickers():
    """Return sorted list of unique ticker symbols (uppercase) from the full dataset."""
    df = load_all_data()
    return sorted(set(df["ticker"].dropna().astype(str).str.upper()))


st.title("Trade Rewind")
st.caption("A tool to understand stock backtesting.")

st.write("")
st.write("#### Learn more")

col1, col2 = st.columns(2)

with col1:
    if st.button(
        "Go to stock information page",
        type="primary",
        use_container_width=True,
    ):
        st.switch_page("pages/stocks_info.py")

with col2:
    if st.button(
        "Go to strategy information page",
        type="primary",
        use_container_width=True,
    ):
        st.switch_page("pages/backtester_info.py")

st.write("")
st.write("#### Configure your backtest")
st.write("")

# Inputs
all_tickers = _available_tickers()

col1, col2, col3 = st.columns(3)
with col1:
    user_stock = st.selectbox(
        "Select a single ticker",
        options=all_tickers,
        index=all_tickers.index("AAPL") if "AAPL" in all_tickers else 0,
    )
with col2:
    start = st.text_input("Start date (YYYY-MM-DD)", placeholder="Optional")
with col3:
    end = st.text_input("End date (YYYY-MM-DD)", placeholder="Optional")

col4, col5 = st.columns(2)
with col4:
    strat = st.selectbox(
        "Choose a strategy",
        options=get_strategy_display_names(),
    )
with col5:
    input_cap = st.number_input(
        "Starting capital",
        min_value=0.0,
        value=10000.0,
        step=500.0,
        format="%.0f",
    )

# Strategy-specific info callout (e.g. Moving Average requirements)
strat_key = display_name_to_key(strat)
if strat_key in STRATEGY_INFO:
    st.info(STRATEGY_INFO[strat_key], icon="📈")

st.write("")
submit_button = st.button("Run backtest", type="primary")

if submit_button:
    # Basic validations
    if not user_stock:
        st.error("Please enter a stock ticker or company name (e.g., AAPL).")
        st.stop()

    start_arg = start or None
    end_arg = end or None

    if start_arg is not None:
        try:
            pd.to_datetime(start_arg, format="%Y-%m-%d")
        except ValueError:
            st.error(
                "Start date must be in the format YYYY-MM-DD "
                "(e.g., 2020-01-01)."
            )
            st.stop()

    if end_arg is not None:
        try:
            pd.to_datetime(end_arg, format="%Y-%m-%d")
        except ValueError:
            st.error(
                "End date must be in the format YYYY-MM-DD "
                "(e.g., 2024-01-01)."
            )
            st.stop()

    if input_cap <= 0:
        st.error("Starting capital must be greater than 0.")
        st.stop()

    # Run backtest
    try:
        results, summary, fig = main_backtest(
            stock=user_stock.upper().strip(),
            start_date=start_arg,
            end_date=end_arg,
            strategy=strat,
            initial_capital=float(input_cap),
        )

    except InvalidTickerError:
        st.error(
            f"Ticker or company '{user_stock}' is not available in the data "
            "or maps to multiple tickers. Please try another symbol or a "
            "more specific company name."
        )
        st.stop()

    except UserWarning as exc:
        st.error(str(exc))
        st.stop()

    except ValueError as exc:
        st.error(str(exc))
        st.stop()

    except Exception as exc:  # pylint: disable=broad-except
        st.error(
            f"An unexpected error occurred while running the backtest: {exc}"
        )
        st.stop()

    # Optional info: notify if requested dates were outside available data.
    if results is not None and hasattr(results, "attrs"):
        requested_start = results.attrs.get("requested_start_date")
        adjusted_start = results.attrs.get("adjusted_start_date")
        if requested_start is not None and adjusted_start is not None:
            st.info(
                "Your requested start date "
                f"{requested_start.strftime('%Y-%m-%d')} is before the earliest "
                f"available data for {user_stock}. Using the earliest available date "
                f"{adjusted_start.strftime('%Y-%m-%d')} instead."
            )

        requested_end = results.attrs.get("requested_end_date")
        adjusted_end = results.attrs.get("adjusted_end_date")
        if requested_end is not None and adjusted_end is not None:
            st.info(
                "Your requested end date "
                f"{requested_end.strftime('%Y-%m-%d')} is after the latest "
                f"available data for {user_stock}. Using the latest available date "
                f"{adjusted_end.strftime('%Y-%m-%d')} instead."
            )

    # Show results
    st.write("### Results")
    if fig is not None:
        st.plotly_chart(fig, use_container_width=True)
    if results is not None:
        st.dataframe(results.head(), use_container_width=True)
