"""Chart builder for the Moving Average Crossover strategy.

Produces a three-panel Plotly figure:

* **Top-left panel**   - portfolio value, daily returns, profit-to-date, and
  drawdown over time, with peak and max-drawdown annotations.
* **Bottom-left panel** - close price overlaid with SMA-50 (blue) and
  SMA-200 (orange), plus green ▲ buy markers and red ▼ sell markers on
  every Golden / Death Cross day.
* **Right panel** (spanning both rows) - scrollable metrics table.
"""

from typing import Any, Dict

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from charts.common import (
    add_initial_capital_line,
    add_metrics_table,
    add_portfolio_traces,
    format_summary,
    prepare_plot_df,
)

# MA-specific trace builders
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

# Public chart builder
def build(
    results_df: pd.DataFrame,
    summary: Dict[str, Any],
    initial_capital: float,
) -> go.Figure:
    """Build the Moving Average Crossover strategy dashboard.

    Args:
        results_df: Strategy results DataFrame from ``moving_average_crossover()``.
            Must contain ``sma_50``, ``sma_200``, ``trade``, and ``close``.
        summary: Metrics dict from ``compute_metrics()``.
        initial_capital: Starting cash used for the reference line.

    Returns:
        A ``plotly.graph_objects.Figure`` ready for ``st.plotly_chart``.
    """
    plot_df = prepare_plot_df(results_df)
    formatted = format_summary(summary)

    fig = make_subplots(
        rows=2,
        cols=2,
        column_widths=[0.7, 0.3],
        row_heights=[0.5, 0.5],
        specs=[
            [{"type": "scatter"}, {"type": "domain", "rowspan": 2}],
            [{"type": "scatter"}, None],
        ],
        horizontal_spacing=0.05,
        vertical_spacing=0.08,
        subplot_titles=[
            "Portfolio Value",
            "",                      # metrics table header (auto-placed)
            "Price & Moving Averages",
        ],
    )

    # Row 1: portfolio performance
    add_portfolio_traces(fig, plot_df, row=1, col=1)
    add_initial_capital_line(fig, initial_capital, row=1, col=1)

    # Row 2: price + SMA overlay + trade markers
    _add_price_and_sma_traces(fig, plot_df, row=2, col=1)
    _add_trade_markers(fig, plot_df, row=2, col=1)

    # Right column: metrics table (spans both rows)
    add_metrics_table(fig, formatted, row=1, col=2)

    fig.update_layout(
        title="Moving Average Crossover (50 / 200 day) - Strategy Dashboard",
        template="plotly_white",
        hovermode="x unified",
        showlegend=True,
    )

    return fig
