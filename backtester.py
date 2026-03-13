"""Backtester orchestration module.

Wires together data loading, strategy dispatch, metric computation, and
chart generation.

Adding a new strategy requires **no changes here** - register it in
``strategies/__init__.py`` instead.
"""

from data_loading import load_all_data
from strategies import run_strategy
from metrics import compute_metrics
from stock_history import get_stock_history
from charts import strategy_dashboard


class InvalidTickerError(Exception):
    """Raised when a requested ticker is not found in the dataset."""


# Load all parquet data once at module import (same pattern as original).
df = load_all_data()


def main_backtest(
    stock: str,
    start_date,
    end_date,
    strategy: str,
    initial_capital: float,
):
    """Run a full backtest and return results, summary metrics, and a chart.

    Args:
        stock: Ticker symbol or company name (e.g. ``"AAPL"``).
        start_date: ISO-format date string or ``None`` (uses earliest date).
        end_date: ISO-format date string or ``None`` (uses latest date).
        strategy: Strategy name, e.g. ``"Buy and Hold"`` or
            ``"Moving Average Crossover"`` (case-insensitive).
        initial_capital: Starting cash in dollars.

    Returns:
        Tuple of ``(results_df, summary_dict, plotly_figure)``.

    Raises:
        InvalidTickerError: If no data is found for *stock*.
        ValueError: Propagated from strategy or date validation.
    """
    if df is None or df.empty:
        raise InvalidTickerError(f"No data found for ticker '{stock}'.")

    prices = get_stock_history(stock, start_date, end_date, df)
    results = run_strategy(prices, strategy, initial_capital, df)
    summary = compute_metrics(results, initial_capital)
    plot = strategy_dashboard(results, summary, initial_capital)

    return results, summary, plot


if __name__ == "__main__":
    results, summary, _ = main_backtest(
        stock="AAPL",
        start_date="2010-01-01",
        end_date="2026-02-19",
        strategy="Moving Average Crossover",
        initial_capital=10000,
    )
    print(
        results[
            [
                "date", "close", "sma_50", "sma_200",
                "signal", "trade", "cash", "position", "daily_value",
            ]
        ].head(10)
    )
    print(summary)
