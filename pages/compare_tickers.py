"""Compare multiple tickers under one or more strategies.

This page reuses the existing pipeline:
- `data_loading.load_all_data`
- `stock_history.get_stock_history`
- `strategies.run_strategy`

It then layers results by ticker on a single Plotly chart per strategy.
"""

import os
import sys
from typing import Any, Callable, Dict, Iterable, List

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

# Add the project folder to the path so imports work when this page runs.
REPO_ROOT = os.path.dirname(os.path.dirname(__file__))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

# These imports need the path above to work. 
# With this, we will have to disable pylint errors for the imports.
# pylint: disable=wrong-import-position,import-error
from data_loading import load_all_data
from metrics import compute_metrics
from stock_history import get_stock_history
from strategies import (
    display_name_to_key,
    get_strategy_display_names,
    run_strategy,
)
from ui_shared import apply_shared_ui

st.set_page_config(page_title="Compare Tickers")  

# Extra charts we can show for some strategies (ex: moving averages).
COMPARISON_EXTRA_PLOTTERS: Dict[str, Callable[..., go.Figure]] = {}


# Labels and display options for each metric we can plot.
PORTFOLIO_SERIES: Dict[str, Dict[str, str]] = {
    "daily_value": {
        "label": "Portfolio value",
        "y_title": "Portfolio value ($)",
        "hover": "%{y:.2f}",
    },
    "daily_returns": {
        "label": "Daily returns",
        "y_title": "Daily returns",
        "hover": "%{y:.4f}",
    },
    "profit_to_date": {
        "label": "Profit to date",
        "y_title": "Profit ($)",
        "hover": "%{y:.2f}",
    },
    "drawdown": {
        "label": "Drawdown",
        "y_title": "Drawdown",
        "hover": "%{y:.4f}",
    },
}

def ticker_colors(ticker_list: Iterable[str]) -> Dict[str, str]:
    """Give each ticker its own color so lines on the chart are easy to tell apart.

    Args:
        ticker_list: The list of ticker symbols to assign colors to.

    Returns:
        A map from each ticker to a color.
    """
    palette = (
        go.Figure().layout.colorway
        or [
            "#636EFA",
            "#EF553B",
            "#00CC96",
            "#AB63FA",
            "#FFA15A",
            "#19D3F3",
            "#FF6692",
            "#B6E880",
            "#FF97FF",
            "#FECB52",
        ]
    )
    mapping: Dict[str, str] = {}
    for idx, ticker_symbol in enumerate(ticker_list):
        mapping[ticker_symbol] = palette[idx % len(palette)]
    return mapping


def prepare_dates(df: pd.DataFrame) -> pd.DataFrame:
    """Make sure the date column is in a simple format so the chart can use it.

    Args:
        df: Table that has a date column.

    Returns:
        A copy of the table with dates cleaned up.
    """
    out = df.copy()
    out["date"] = pd.to_datetime(out["date"]).dt.tz_localize(None)
    return out


def plot_portfolio_value(
    results_by_ticker: Dict[str, pd.DataFrame],  # pylint: disable=redefined-outer-name
    initial_capital: float,  # pylint: disable=redefined-outer-name
) -> go.Figure:
    """Draw one line per ticker showing how much the portfolio is worth each day.

    Args:
        results_by_ticker: Results for each ticker.
        initial_capital: Starting money (shown as a line on the chart).

    Returns:
        A chart with one line per ticker.
    """
    return plot_portfolio_series(
        results_by_ticker=results_by_ticker,
        series_keys=["daily_value"],
        initial_capital=initial_capital,
        title="Portfolio metrics (layered by ticker)",
    )


def plot_portfolio_series(
    results_by_ticker: Dict[str, pd.DataFrame],  # pylint: disable=redefined-outer-name
    series_keys: List[str],
    initial_capital: float,  # pylint: disable=redefined-outer-name
    title: str,
) -> go.Figure:
    """Draw one or more metrics with one line per ticker.

    If you pick several metrics, each gets its own row on the chart. We also
    draw a line for your starting capital on the value chart.

    Args:
        results_by_ticker: Results for each ticker.
        series_keys: Which metrics to plot (e.g. daily_value, drawdown).
        initial_capital: Starting money (shown as a line on the chart).
        title: Title at the top of the chart.

    Returns:
        A chart with one row per metric and one line per ticker.
    """
    valid_keys = [k for k in series_keys if k in PORTFOLIO_SERIES]
    if not valid_keys:
        valid_keys = ["daily_value"]

    colors = ticker_colors(results_by_ticker.keys())
    fig = make_subplots(  # pylint: disable=redefined-outer-name
        rows=len(valid_keys),
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.08,
        subplot_titles=[PORTFOLIO_SERIES[k]["label"] for k in valid_keys],
    )

    for row_idx, series_key in enumerate(valid_keys, start=1):
        meta = PORTFOLIO_SERIES[series_key]
        for ticker_symbol, res in results_by_ticker.items():
            plot_df = prepare_dates(res)
            if series_key not in plot_df.columns:
                continue
            fig.add_trace(
                go.Scatter(
                    x=plot_df["date"],
                    y=plot_df[series_key],
                    mode="lines",
                    name=ticker_symbol,
                    legendgroup=ticker_symbol,
                    showlegend=(row_idx == 1),
                    line={"color": colors[ticker_symbol], "width": 2},
                    hovertemplate=(
                        f"{ticker_symbol} - {series_key}: {meta['hover']}"
                        "<br>Date: %{x}<extra></extra>"
                    ),
                ),
                row=row_idx,
                col=1,
            )

        fig.update_yaxes(title_text=meta["y_title"], row=row_idx, col=1)

        if series_key == "daily_value":
            fig.add_hline(
                y=initial_capital,
                line_dash="dash",
                line_color="green",
                annotation_text="Initial Capital",
                annotation_position="bottom right",
                row=row_idx,
                col=1,
            )

    fig.update_layout(
        title=title,
        template="plotly_white",
        hovermode="x unified",
        showlegend=True,
    )
    fig.update_xaxes(title_text="Date", row=len(valid_keys), col=1)
    return fig


def plot_moving_averages(
    results_by_ticker: Dict[str, pd.DataFrame],  # pylint: disable=redefined-outer-name
    _initial_capital: float,  # not used; here so this function matches the others
) -> go.Figure:
    """Draw each ticker's price and its 50-day and 200-day averages by color.

    Args:
        results_by_ticker: Results for each ticker (need price and both averages).
        _initial_capital: Not used; only here so this function matches the others.

    Returns:
        A chart with price and average lines for each ticker.
    """
    colors = ticker_colors(results_by_ticker.keys())
    fig = go.Figure()  # pylint: disable=redefined-outer-name

    for ticker_symbol, res in results_by_ticker.items():
        plot_df = prepare_dates(res)
        color = colors[ticker_symbol]

        if "close" in plot_df.columns:
            fig.add_trace(
                go.Scatter(
                    x=plot_df["date"],
                    y=plot_df["close"],
                    mode="lines",
                    name=f"{ticker_symbol} Close",
                    line={"color": color, "width": 1},
                    opacity=0.45,
                    hovertemplate=(
                        f"{ticker_symbol} - close: %{{y:.2f}}"
                        "<br>Date: %{x}<extra></extra>"
                    ),
                )
            )

        if "sma_50" in plot_df.columns:
            fig.add_trace(
                go.Scatter(
                    x=plot_df["date"],
                    y=plot_df["sma_50"],
                    mode="lines",
                    name=f"{ticker_symbol} SMA 50",
                    line={"color": color, "width": 2, "dash": "solid"},
                    hovertemplate=(
                        f"{ticker_symbol} - SMA 50: %{{y:.2f}}"
                        "<br>Date: %{x}<extra></extra>"
                    ),
                )
            )

        if "sma_200" in plot_df.columns:
            fig.add_trace(
                go.Scatter(
                    x=plot_df["date"],
                    y=plot_df["sma_200"],
                    mode="lines",
                    name=f"{ticker_symbol} SMA 200",
                    line={"color": color, "width": 2, "dash": "dash"},
                    hovertemplate=(
                        f"{ticker_symbol} - SMA 200: %{{y:.2f}}"
                        "<br>Date: %{x}<extra></extra>"
                    ),
                )
            )

    fig.update_layout(
        title="Moving Averages (layered by ticker)",
        template="plotly_white",
        hovermode="x unified",
        showlegend=True,
        yaxis_title="Price ($)",
        xaxis_title="Date",
    )
    return fig


# Hook up the extra chart for strategies that support it (here: moving averages).
COMPARISON_EXTRA_PLOTTERS["moving average crossover"] = plot_moving_averages


@st.cache_data(show_spinner=False)
def load_data_cached() -> pd.DataFrame:
    """Load all the stock data once and remember it so we don't load again."""
    return load_all_data()


def available_tickers(data_df: pd.DataFrame) -> List[str]:
    """Get a sorted list of all ticker symbols in the data."""
    return sorted(set(data_df["ticker"].dropna().astype(str).str.upper()))


apply_shared_ui()

# Compare Tickers page: title and back button
st.title("Compare Tickers")
st.caption("Layer multiple tickers on the same strategy chart.")

if st.button("Back to main page", type="secondary"):
    st.switch_page("home_page.py")

data = load_data_cached()
all_tickers = available_tickers(data)

st.write("")
st.write("#### Configure comparison")

col1, col2, col3 = st.columns(3)
with col1:
    selected_tickers = st.multiselect(
        "Select tickers (2+ recommended)",
        options=all_tickers,
        default=["AAPL"] if "AAPL" in all_tickers else [],
    )
with col2:
    start = st.text_input("Start date (YYYY-MM-DD)", placeholder="Optional")
with col3:
    end = st.text_input("End date (YYYY-MM-DD)", placeholder="Optional")

col4, col5, col6 = st.columns(3)
with col4:
    selected_strategies = st.multiselect(
        "Choose strategy/strategies",
        options=get_strategy_display_names(),
        default=["Buy and Hold"] if "Buy and Hold" in get_strategy_display_names() else [],
    )
with col5:
    initial_capital = st.number_input(
        "Starting capital",
        min_value=0.0,
        value=10000.0,
        step=500.0,
        format="%.0f",
    )
with col6:
    selected_series = st.multiselect(
        "Portfolio series to plot",
        options=list(PORTFOLIO_SERIES.keys()),
        default=["daily_value"],
        help=(
            "Choose what to visualize across tickers. "
            "If you select multiple, you'll get one subplot per series."
        ),
    )

run = st.button("Run comparison", type="primary")

if run:
    if len(selected_tickers) < 1:
        st.error("Please select at least one ticker.")
        st.stop()

    if len(selected_strategies) < 1:
        st.error("Please select at least one strategy.")
        st.stop()

    if initial_capital <= 0:
        st.error("Starting capital must be greater than 0.")
        st.stop()

    start_arg = start or None
    end_arg = end or None

    # Check that any dates the user typed are in the right format.
    for date_label, date_value in (("Start date", start_arg), ("End date", end_arg)):
        if date_value is None:
            continue
        try:
            pd.to_datetime(date_value, format="%Y-%m-%d")
        except ValueError:
            st.error(f"{date_label} must be in the format YYYY-MM-DD (e.g., 2020-01-01).")
            st.stop()

    st.write("")
    st.write("### Results")

    # For each strategy, run it for every ticker and draw one chart with all of them.
    for strategy_name in selected_strategies:
        strategy_key = display_name_to_key(strategy_name)
        st.write(f"#### {strategy_name}")

        results_by_ticker: Dict[str, pd.DataFrame] = {}
        metric_rows: List[Dict[str, Any]] = []

        for ticker in selected_tickers:
            try:
                prices = get_stock_history(ticker, start_arg, end_arg, data)
                results = run_strategy(prices, strategy_name, float(initial_capital), data)
                summary = compute_metrics(results, float(initial_capital))
            except (ValueError, TypeError, UserWarning) as exc:
                st.warning(f"{ticker}: {exc}")
                continue
            except Exception as exc:  # pylint: disable=broad-except
                st.warning(f"{ticker}: Unexpected error: {exc}")
                continue

            results_by_ticker[ticker] = results
            metric_rows.append(
                {
                    "ticker": ticker,
                    "Total Return": summary.get("Total Return"),
                    "Annualized Return": summary.get("Annualized Return"),
                    "Annualized Sharpe Ratio": summary.get("Annualized Sharpe Ratio"),
                    "Max Drawdown": summary.get("Max Drawdown"),
                }
            )

        if not results_by_ticker:
            st.info("No results to plot for this strategy (all selections errored).")
            continue

        if selected_series:
            fig = plot_portfolio_series(
                results_by_ticker=results_by_ticker,
                series_keys=selected_series,
                initial_capital=float(initial_capital),
                title=f"{strategy_name} - Portfolio metrics (layered by ticker)",
            )
            st.plotly_chart(fig, use_container_width=True)

        if strategy_key in COMPARISON_EXTRA_PLOTTERS:
            extra_plotter = COMPARISON_EXTRA_PLOTTERS[strategy_key]
            st.write("##### Extra chart")
            st.plotly_chart(
                extra_plotter(results_by_ticker, float(initial_capital)),
                use_container_width=True,
            )

        if metric_rows:
            metrics_df = pd.DataFrame(metric_rows).set_index("ticker")
            st.dataframe(metrics_df, use_container_width=True)
