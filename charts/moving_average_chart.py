"""Chart builder for the Moving Average Crossover strategy.

Produces a full-width two-panel Plotly figure:

* **Top panel** — portfolio value, daily returns, profit-to-date, and
  drawdown over time, with peak and max-drawdown annotations.
* **Bottom panel** — close price overlaid with SMA-50 (blue) and
  SMA-200 (orange), plus green ▲ buy markers and red ▼ sell markers on
  every Golden / Death Cross day.

The metrics table is rendered separately by the caller (home_page.py)
using ``charts.common.format_summary`` so it can be displayed below the
chart at full width.
"""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from charts.common import (
    add_initial_capital_line,
    add_portfolio_traces,
    prepare_plot_df,
)


def _add_price_and_sma_traces(
    fig: go.Figure,
    sma_df: pd.DataFrame,
    row: int,
    col: int,
) -> None:
    """Overlay close price with SMA-50 and SMA-200 lines.

    Args:
        fig: Plotly figure to mutate.
        sma_df: Strategy results DataFrame (must contain ``sma_50``, ``sma_200``).
        row: Subplot row index (1-based).
        col: Subplot column index (1-based).
    """
    fig.add_trace(
        go.Scatter(
            x=sma_df["date"],
            y=sma_df["close"],
            mode="lines",
            name="Close",
            line={"color": "lightgrey", "width": 1},
            hovertemplate="Close: %{y:.2f}<br>Date: %{x}<extra></extra>",
        ),
        row=row,
        col=col,
    )
    fig.add_trace(
        go.Scatter(
            x=sma_df["date"],
            y=sma_df["sma_50"],
            mode="lines",
            name="SMA 50",
            line={"color": "royalblue", "width": 1.5},
            hovertemplate="SMA 50: %{y:.2f}<br>Date: %{x}<extra></extra>",
        ),
        row=row,
        col=col,
    )
    fig.add_trace(
        go.Scatter(
            x=sma_df["date"],
            y=sma_df["sma_200"],
            mode="lines",
            name="SMA 200",
            line={"color": "darkorange", "width": 1.5},
            hovertemplate="SMA 200: %{y:.2f}<br>Date: %{x}<extra></extra>",
        ),
        row=row,
        col=col,
    )


def _add_trade_markers(
    fig: go.Figure,
    trade_df: pd.DataFrame,
    row: int,
    col: int,
) -> None:
    """Plot Golden Cross (buy) and Death Cross (sell) markers on the price panel.

    Args:
        fig: Plotly figure to mutate.
        trade_df: Strategy results DataFrame (must contain ``trade`` and ``close``).
        row: Subplot row index (1-based).
        col: Subplot column index (1-based).
    """
    buys = trade_df[trade_df["trade"] == 1]
    if not buys.empty:
        fig.add_trace(
            go.Scatter(
                x=buys["date"],
                y=buys["close"],
                mode="markers",
                marker={"symbol": "triangle-up", "size": 12, "color": "green"},
                name="Buy (Golden Cross)",
                hovertemplate="BUY @ %{y:.2f}<br>Date: %{x}<extra></extra>",
            ),
            row=row,
            col=col,
        )

    sells = trade_df[trade_df["trade"] == -1]
    if not sells.empty:
        fig.add_trace(
            go.Scatter(
                x=sells["date"],
                y=sells["close"],
                mode="markers",
                marker={
                    "symbol": "triangle-down",
                    "size": 12,
                    "color": "crimson",
                },
                name="Sell (Death Cross)",
                hovertemplate="SELL @ %{y:.2f}<br>Date: %{x}<extra></extra>",
            ),
            row=row,
            col=col,
        )


def build(
    results_df: pd.DataFrame,
    summary: dict,  #noqa: ARG001 — unused here; rendered separately by caller
    initial_capital: float,
) -> go.Figure:
    """Build the Moving Average Crossover chart (full width, no table).

    Args:
        results_df: Strategy results DataFrame from ``moving_average_crossover()``.
            Must contain ``sma_50``, ``sma_200``, ``trade``, and ``close``.
        summary: Metrics dict (unused here; rendered separately by caller).
        initial_capital: Starting cash used for the reference line.

    Returns:
        A full-width ``plotly.graph_objects.Figure`` ready for
        ``st.plotly_chart(fig, use_container_width=True)``.
    """
    plot_df = prepare_plot_df(results_df)

    fig = make_subplots(
        rows=2,
        cols=1,
        row_heights=[0.5, 0.5],
        shared_xaxes=True,
        vertical_spacing=0.08,
        subplot_titles=["Portfolio Performance", "Price & Moving Averages"],
    )

    # Row 1: portfolio performance
    add_portfolio_traces(fig, plot_df, row=1, col=1)
    add_initial_capital_line(fig, initial_capital, row=1, col=1)

    # Row 2: price + SMA overlay + trade markers
    _add_price_and_sma_traces(fig, plot_df, row=2, col=1)
    _add_trade_markers(fig, plot_df, row=2, col=1)

    fig.update_layout(
        title="Moving Average Crossover (50 / 200 day) — Strategy Dashboard",
        template="plotly_white",
        hovermode="x unified",
        showlegend=True,
        height=750,
        margin={"t": 80, "b": 40, "l": 60, "r": 40},
    )

    fig.update_yaxes(title_text="Portfolio Value ($)", row=1, col=1)
    fig.update_yaxes(title_text="Price ($)", row=2, col=1)
    fig.update_xaxes(title_text="Date", row=2, col=1)

    return fig
