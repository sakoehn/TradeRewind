"""Streamlit home page for TradeRewind.

Provides the main UI for configuring and running a backtest.
"""

import streamlit as st
import pandas as pd

from backtester import main_backtest, InvalidTickerError

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
col1, col2, col3 = st.columns(3)
with col1:
    user_stock = st.text_input(
        "Enter stock ticker or company",
        placeholder="AAPL",
    )
with col2:
    start = st.text_input("Start date (YYYY-MM-DD)", placeholder="Optional")
with col3:
    end = st.text_input("End date (YYYY-MM-DD)", placeholder="Optional")

col4, col5 = st.columns(2)
with col4:
    options = ["Buy and Hold", "Moving Average Crossover"]
    strat = st.selectbox("Choose a strategy", options)
with col5:
    input_cap = st.number_input(
        "Starting capital",
        min_value=0.0,
        value=10000.0,
        step=500.0,
        format="%.0f",
    )

#  Moving Average info callout
if strat == "Moving Average Crossover":
    st.info(
        "**Moving Average Crossover (50 / 200 day)**  \n"
        "Buys when the 50-day SMA crosses above the 200-day SMA *(Golden "
        "Cross)* and sells when it crosses below *(Death Cross)*.  \n"
        "Requires **at least 201 trading days** (~1 year) of data. "
        "Widen your date range if you see an error.",
        icon="📈",
    )

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
        results, summary, fig, metrics_df = main_backtest(
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

    # Show results
    st.write("### Results")
 
    # Full-width chart
    if fig is not None:
        st.plotly_chart(fig, use_container_width=True)
 
    # Metrics cards — 3 per row
    if metrics_df is not None and not metrics_df.empty:
        st.write("#### Performance Metrics")
        metrics = list(metrics_df.itertuples(index=False, name=None))
        cols_per_row = 3
        for row_start in range(0, len(metrics), cols_per_row):
            row_metrics = metrics[row_start: row_start + cols_per_row]
            cols = st.columns(cols_per_row)
            for col, (metric, value) in zip(cols, row_metrics):
                col.metric(label=metric, value=value)
