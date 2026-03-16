"""Chart package for TradeRewind.

Each strategy that needs a custom visualisation has its own module here.
Shared building blocks live in ``charts.common``.

``strategy_dashboard`` is the single entry point used by backtester.py;
it routes to the correct chart module based on the strategy name and
returns a ``(figure, metrics_df)`` tuple so the caller can render the
chart and metrics table independently (chart full-width, table below).

Adding a chart for a new strategy
----------------------------------
1. Create  ``charts/my_strategy_chart.py``  with a ``build(df, summary,
   initial_capital) -> go.Figure`` function.
2. Import it below.
3. Add a branch inside ``strategy_dashboard``.
"""

import pandas as pd
import plotly.graph_objects as go

from charts.common import build_metrics_df, format_summary
from charts.buy_and_hold_chart import build as _build_buy_and_hold
from charts.moving_average_chart import build as _build_moving_average
from charts.momentum_chart import build as _build_momentum


def strategy_dashboard(
    results_df: pd.DataFrame,
    strategy: str,
    summary: dict,
    initial_capital: float,
) -> tuple[go.Figure, pd.DataFrame]:
    """Route to the correct chart builder and return figure + metrics table.

    Args:
        results_df: Strategy results DataFrame (output of any strategy function).
        strategy: Strategy name string (case-insensitive), e.g.
            ``"Buy and Hold"`` or ``"Moving Average Crossover"``.
        summary: Raw metrics dict from ``compute_metrics``.
        initial_capital: Starting cash (used for the reference line).

    Returns:
        Tuple of ``(plotly_figure, metrics_dataframe)``.
        The figure is full-width and has no embedded table.
        The DataFrame has columns ``["Metric", "Value"]`` ready for
        ``st.dataframe`` or ``st.table``.

    Raises:
        ValueError: If *strategy* is not a recognised strategy name.
    """
    formatted = format_summary(summary)
    metrics_df = build_metrics_df(formatted)

    key = strategy.lower().strip()

    if key == "buy and hold":
        fig = _build_buy_and_hold(results_df, summary, initial_capital)
    elif key == "moving average crossover":
        fig = _build_moving_average(results_df, summary, initial_capital)
    elif key == "momentum":
        fig = _build_momentum(results_df, summary, initial_capital)
    else:
        raise ValueError(
            f"'{strategy}' is not a recognised strategy. "
            "Check strategies/REGISTRY for valid names."
        )

    return fig, metrics_df


__all__ = [
    "strategy_dashboard",
    "format_summary",
    "build_metrics_df",
]
