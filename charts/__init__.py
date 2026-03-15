"""Chart package for TradeRewind.

Each strategy that needs a custom visualisation has its own module here.
Shared building blocks live in ``charts.common``.

``strategy_dashboard`` is the single entry point used by backtester.py;
it auto-routes to the correct chart module based on the result columns
present in the DataFrame.

Adding a chart for a new strategy
----------------------------------
1. Create  ``charts/my_strategy_chart.py``  with a ``build(df, summary,
   initial_capital) -> go.Figure`` function.
2. Import it below.
3. Add a detection condition inside ``strategy_dashboard``.
"""

from typing import Any, Dict

import pandas as pd
import plotly.graph_objects as go

from charts.buy_and_hold_chart import build as _build_buy_and_hold
from charts.common import add_metrics_table, add_portfolio_traces, format_summary
from charts.moving_average_chart import build as _build_moving_average


def strategy_dashboard(
    results_df: pd.DataFrame,
    summary: Dict[str, Any],
    initial_capital: float,
) -> go.Figure:
    """Route to the correct chart builder based on strategy output columns.

    Args:
        results_df: Strategy results DataFrame (output of any strategy function).
        summary: Metrics dict from ``compute_metrics``.
        initial_capital: Starting cash (used for the reference line).

    Returns:
        A ``plotly.graph_objects.Figure`` ready for display.
    """
    # sma_50 is only added by the MA strategy — never present in raw parquet data.
    # This is the unambiguous routing signal.
    if "trade" in results_df.columns:
        return _build_moving_average(results_df, summary, initial_capital)

    return _build_buy_and_hold(results_df, summary, initial_capital)


__all__ = [
    "strategy_dashboard",
    "format_summary",
    "add_portfolio_traces",
    "add_metrics_table",
]
