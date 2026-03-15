"""Chart builder for the Buy-and-Hold strategy.

Produces a two-panel Plotly figure:

* **Left panel** - portfolio value, daily returns, profit-to-date, and
  drawdown over time, with peak and max-drawdown annotations.
* **Right panel** - scrollable metrics table.
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


def build(
    results_df: pd.DataFrame,
    summary: Dict[str, Any],
    initial_capital: float,
) -> go.Figure:
    """Build the Buy-and-Hold strategy dashboard.

    Args:
        results_df: Strategy results DataFrame from ``buy_and_hold()``.
        summary: Metrics dict from ``compute_metrics()``.
        initial_capital: Starting cash used for the reference line.

    Returns:
        A ``plotly.graph_objects.Figure`` ready for ``st.plotly_chart``.
    """
    plot_df = prepare_plot_df(results_df)
    formatted = format_summary(summary)

    fig = make_subplots(
        rows=1,
        cols=2,
        column_widths=[0.7, 0.3],
        specs=[[{"type": "scatter"}, {"type": "domain"}]],
        horizontal_spacing=0.05,
    )

    add_portfolio_traces(fig, plot_df, row=1, col=1)
    add_initial_capital_line(fig, initial_capital, row=1, col=1)
    add_metrics_table(fig, formatted, row=1, col=2)

    fig.update_layout(
        title="Buy and Hold - Strategy Dashboard",
        template="plotly_white",
        hovermode="x unified",
        showlegend=True,
    )

    return fig
