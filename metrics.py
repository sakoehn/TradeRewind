"""Performance metrics for TradeRewind backtests.

``compute_metrics`` accepts the enriched DataFrame produced by any strategy
function and returns a flat dict of scalar metrics ready for display.
"""

from typing import Any, Dict

import numpy as np
import pandas as pd


def compute_metrics(  # pylint: disable=too-many-locals
    results_df: pd.DataFrame, initial_capital: float
) -> Dict[str, Any]:
    """Compute a comprehensive set of back-test performance metrics.

    Args:
        results_df: Enriched strategy results DataFrame.  Must contain
            ``daily_value``, ``daily_returns``, ``close``, ``sma_200``,
            ``return_1d``, ``return_5d``, ``return_20d``, ``rsi_14``,
            ``atr_14``, ``volatility_20d``, and ``volume_ratio``.
        initial_capital: Starting cash in dollars (used as the denominator
            for return calculations).

    Returns:
        Dict of metric name → scalar value (float).
    """
    result = results_df.copy()
    result = result.dropna(subset=["daily_value", "daily_returns"])

    daily_returns = result["daily_returns"]

    # Calculated metrics
    total_return = (result["daily_value"].iloc[-1] / initial_capital) - 1

    annualized_return = (1 + total_return) ** (252 / len(result)) - 1

    annualized_sharpe_ratio = (
        daily_returns.mean() / daily_returns.std()
    ) * np.sqrt(252)

    max_drawdown = (
        result["daily_value"] / result["daily_value"].cummax() - 1
    ).min()

    annual_volatility = daily_returns.std() * np.sqrt(252)

    win_rate = (daily_returns > 0).mean()

    # Metrics derived from the enriched dataset columns
    avg_return_1d = result["return_1d"].mean()
    avg_return_5d = result["return_5d"].mean()
    avg_return_20d = result["return_20d"].mean()
    pct_above_sma_200 = (result["close"] > result["sma_200"]).mean()
    avg_rsi = result["rsi_14"].mean()
    avg_atr = result["atr_14"].mean()
    avg_volatility_20d = result["volatility_20d"].mean()
    avg_volume_ratio = result["volume_ratio"].mean()

    return {
        # Calculated metrics
        "Total Return": total_return,
        "Annualized Return": annualized_return,
        "Annualized Sharpe Ratio": annualized_sharpe_ratio,
        "Max Drawdown": max_drawdown,
        "Annualized Volatility": annual_volatility,
        "Win Rate": win_rate,
        # Dataset-derived metrics
        "Avg 1D Return": avg_return_1d,
        "Avg 5D Return": avg_return_5d,
        "Avg 20D Return": avg_return_20d,
        "% Above SMA200": pct_above_sma_200,
        "Average RSI": avg_rsi,
        "Average ATR": avg_atr,
        "Average 20D Volatility": avg_volatility_20d,
        "Average Volume Ratio": avg_volume_ratio,
    }
