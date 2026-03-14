"""Shared chart utilities for TradeRewind.

All functions here are pure - they mutate a Plotly figure passed in but
never own one themselves, making them easy to compose across strategy
chart modules.
"""

import pandas as pd
import plotly.graph_objects as go

# Metric labels: raw key -> human-readable display name
_METRIC_LABELS = {
    "total_return":          "Total Return",
    "annualized_return":     "Annualized Return",
    "annualized_sharpe":     "Sharpe Ratio (Annualized)",
    "max_drawdown":          "Max Drawdown",
    "annualized_volatility": "Annualized Volatility",
    "win_rate":              "Win Rate",
    "profit_factor":         "Profit Factor",
    "avg_win":               "Average Win",
    "avg_loss":              "Average Loss",
    "total_trades":          "Total Trades",
    "calmar_ratio":          "Calmar Ratio",
    "sortino_ratio":         "Sortino Ratio",
}


def format_summary(summary: dict) -> dict:
    """Convert raw metric floats to human-readable strings.

    * Values whose key contains ``"return"``, ``"drawdown"``,
      ``"volatility"``, or ``"rate"`` are rendered as percentages.
    * All other floats get two decimal places.
    * Non-float values are converted with ``str()``.

    Args:
        summary: Raw metrics dict (floats and other types).

    Returns:
        New dict mapping human-readable labels to formatted string values.
    """
    pct_keys = {"return", "drawdown", "volatility", "rate"}
    formatted: dict = {}
    for key, value in summary.items():
        label = _METRIC_LABELS.get(key, key.replace("_", " ").title())
        if isinstance(value, float):
            if any(p in key.lower() for p in pct_keys):
                formatted[label] = f"{value * 100:.2f}%"
            else:
                formatted[label] = f"{value:.2f}"
        else:
            formatted[label] = str(value)
    return formatted


def build_metrics_df(summary: dict) -> pd.DataFrame:
    """Convert a formatted summary dict into a two-column DataFrame.

    Intended for use with ``st.dataframe`` or ``st.table`` in home_page.py.

    Args:
        summary: Already-formatted metrics dict produced by ``format_summary``.

    Returns:
        DataFrame with columns ``["Metric", "Value"]``, one row per metric.
    """
    return pd.DataFrame(
        {"Metric": list(summary.keys()), "Value": list(summary.values())}
    )


def add_portfolio_traces(
    fig: go.Figure,
    plot_df: pd.DataFrame,
    row: int,
    col: int,
) -> None:
    """Add portfolio value, daily returns, profit-to-date, and drawdown lines.

    Also annotates the peak portfolio value and the maximum drawdown point.

    Args:
        fig: Plotly figure to mutate.
        plot_df: Strategy results DataFrame (must have ``date`` and
            ``daily_value`` columns; others are optional).
        row: Subplot row index (1-based).
        col: Subplot column index (1-based).
    """
    columns_to_plot = [
        "daily_value",
        "daily_returns",
        "profit_to_date",
        "drawdown",
    ]
    available = [c for c in columns_to_plot if c in plot_df.columns]

    for col_name in available:
        hover_fmt = (
            f"{col_name}: %{{y:.4f}}<br>Date: %{{x}}<extra></extra>"
            if col_name == "daily_returns"
            else f"{col_name}: %{{y:.2f}}<br>Date: %{{x}}<extra></extra>"
        )
        fig.add_trace(
            go.Scatter(
                x=plot_df["date"],
                y=plot_df[col_name],
                mode="lines",
                name=col_name,
                hovertemplate=hover_fmt,
            ),
            row=row,
            col=col,
        )

    # Annotation: peak portfolio value
    if "daily_value" in plot_df.columns and not plot_df.empty:
        peak_idx = plot_df["daily_value"].idxmax()
        fig.add_trace(
            go.Scatter(
                x=[plot_df["date"][peak_idx]],
                y=[plot_df["daily_value"][peak_idx]],
                mode="markers+text",
                marker={"size": 12, "color": "red"},
                text=["Peak Portfolio"],
                textposition="top center",
                name="Peak Value",
            ),
            row=row,
            col=col,
        )

    # Annotation: maximum drawdown point
    if "drawdown" in plot_df.columns and not plot_df.empty:
        dd_idx = plot_df["drawdown"].idxmin()
        fig.add_trace(
            go.Scatter(
                x=[plot_df["date"][dd_idx]],
                y=[plot_df["daily_value"][dd_idx]],
                mode="markers+text",
                marker={"size": 12, "color": "black"},
                text=["Max Drawdown"],
                textposition="bottom center",
                name="Max Drawdown",
            ),
            row=row,
            col=col,
        )


def add_initial_capital_line(
    fig: go.Figure,
    initial_capital: float,
    row: int,
    col: int,
) -> None:
    """Draw a dashed horizontal reference line at ``initial_capital``.

    Args:
        fig: Plotly figure to mutate.
        initial_capital: Dollar value for the reference line.
        row: Subplot row index (1-based).
        col: Subplot column index (1-based).
    """
    fig.add_hline(
        y=initial_capital,
        line_dash="dash",
        line_color="green",
        annotation_text="Initial Capital",
        annotation_position="bottom right",
        row=row,
        col=col,
    )


def prepare_plot_df(raw_df: pd.DataFrame) -> pd.DataFrame:
    """Sanitise a strategy results DataFrame for plotting.

    * Strips timezone from ``date`` so Plotly renders it without offset text.
    * Drops rows where ``daily_value`` or ``daily_returns`` are NaN.
    * Resets the integer index so positional lookups are safe.

    Args:
        raw_df: Raw strategy results DataFrame.

    Returns:
        Clean copy ready for charting.
    """
    plot_df = raw_df.copy()
    plot_df["date"] = pd.to_datetime(plot_df["date"]).dt.tz_localize(None)
    plot_df = plot_df.dropna(subset=["daily_value", "daily_returns"])
    plot_df = plot_df.reset_index(drop=True)
    return plot_df

