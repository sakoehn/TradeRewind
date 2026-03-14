"""Chart builder for the Buy-and-Hold strategy.

Produces a single full-width Plotly figure:

* Portfolio value, daily returns, profit-to-date, and drawdown over time.
* Peak portfolio value and max-drawdown annotations.
* Dashed initial capital reference line.

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


def build(
    results_df: pd.DataFrame,
    summary: dict,  # noqa: ARG001 — unused here; kept for API parity
    initial_capital: float,
) -> go.Figure:
    """Build the Buy-and-Hold strategy chart (full width, no table).

    Args:
        results_df: Strategy results DataFrame from ``buy_and_hold()``.
        summary: Metrics dict (unused here; rendered separately by caller).
        initial_capital: Starting cash used for the reference line.

    Returns:
        A full-width ``plotly.graph_objects.Figure`` ready for
        ``st.plotly_chart(fig, use_container_width=True)``.
    """
    plot_df = prepare_plot_df(results_df)

    fig = make_subplots(
        rows=1,
        cols=1,
        subplot_titles=["Portfolio Performance"],
    )

    add_portfolio_traces(fig, plot_df, row=1, col=1)
    add_initial_capital_line(fig, initial_capital, row=1, col=1)

    fig.update_layout(
        title="Buy and Hold — Strategy Dashboard",
        template="plotly_white",
        hovermode="x unified",
        showlegend=True,
        height=500,
        margin={"t": 80, "b": 40, "l": 60, "r": 40},
    )

    fig.update_xaxes(title_text="Date", row=1, col=1)
    fig.update_yaxes(title_text="Portfolio Value ($)", row=1, col=1)

    return fig

