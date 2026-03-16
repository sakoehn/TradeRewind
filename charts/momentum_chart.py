"""Chart builder for the Momentum strategy.

Produces a full-width two-panel Plotly figure:

* **Top panel** — portfolio value, daily returns, profit-to-date, and
  drawdown over time, with peak and max-drawdown annotations.
* **Bottom panel** — close price with green ▲ buy markers and red ▼ sell
  markers on every trade day.
"""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from charts.common import (
    add_initial_capital_line,
    add_portfolio_traces,
    prepare_plot_df,
)


def _add_price_trace(fig, plot_df, row, col):
    """Overlay close price line."""
    fig.add_trace(
        go.Scatter(
            x=plot_df["date"],
            y=plot_df["close"],
            mode="lines",
            name="Close",
            line={"color": "lightgrey", "width": 1},
            hovertemplate="Close: %{y:.2f}<br>Date: %{x}<extra></extra>",
        ),
        row=row,
        col=col,
    )


def _add_trade_markers(fig, trade_df, row, col):
    """Plot buy and sell markers on the price panel."""
    buys = trade_df[trade_df["trade"] == 1]
    if not buys.empty:
        fig.add_trace(
            go.Scatter(
                x=buys["date"],
                y=buys["close"],
                mode="markers",
                marker={"symbol": "triangle-up", "size": 10, "color": "green"},
                name="Buy",
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
                marker={"symbol": "triangle-down", "size": 10, "color": "crimson"},
                name="Sell",
                hovertemplate="SELL @ %{y:.2f}<br>Date: %{x}<extra></extra>",
            ),
            row=row,
            col=col,
        )


def build(
    results_df: pd.DataFrame,
    summary: dict,  # noqa: ARG001
    initial_capital: float,
) -> go.Figure:
    """Build the Momentum strategy chart (full width, no table).

    Args:
        results_df: Strategy results DataFrame from ``momentum()``.
        summary: Metrics dict (unused; rendered separately by caller).
        initial_capital: Starting cash used for the reference line.

    Returns:
        A full-width ``plotly.graph_objects.Figure``.
    """
    plot_df = prepare_plot_df(results_df)

    fig = make_subplots(
        rows=2,
        cols=1,
        row_heights=[0.5, 0.5],
        shared_xaxes=True,
        vertical_spacing=0.08,
        subplot_titles=["Portfolio Performance", "Price & Trade Signals"],
    )

    add_portfolio_traces(fig, plot_df, row=1, col=1)
    add_initial_capital_line(fig, initial_capital, row=1, col=1)

    _add_price_trace(fig, plot_df, row=2, col=1)
    _add_trade_markers(fig, plot_df, row=2, col=1)

    fig.update_layout(
        title="Momentum — Strategy Dashboard",
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
