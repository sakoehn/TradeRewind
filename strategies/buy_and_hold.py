"""Buy-and-hold strategy for TradeRewind.

Buys all available shares on the first day and holds until the end of the
back-test period.  This is the simplest benchmark strategy.

Strategy contract
-----------------
The returned DataFrame contains every original column plus:

    position       - constant number of shares held
    price          - alias for ``close``
    daily_value    - portfolio value each day (shares * price)
    daily_returns  - percentage change in portfolio value day-over-day
    profit_to_date - cumulative profit / loss vs. ``initial_capital``
    drawdown       - rolling drawdown from the running portfolio peak
"""

import pandas as pd


def buy_and_hold(
    prices: pd.DataFrame,
    initial_capital: float,
    full_df: pd.DataFrame,  # noqa: ARG001 - unused; kept for strategy API parity
) -> pd.DataFrame:
    """Buy all shares on day 1 and hold until the end of the period.

    Args:
        prices: Date-filtered, single-stock DataFrame with a ``close`` column.
        initial_capital: Starting cash in dollars.
        full_df: Full combined dataset; unused but required by the strategy API
            so all strategies share the same call signature.

    Returns:
        Enriched DataFrame with strategy columns appended.
    """
    result = prices.copy()

    first_price = float(result["close"].iloc[0])
    shares = initial_capital / first_price

    result["position"] = shares
    result["price"] = result["close"]
    result["daily_value"] = result["position"] * result["price"]
    result["daily_returns"] = result["daily_value"].pct_change().fillna(0)
    result["profit_to_date"] = result["daily_value"] - initial_capital
    result["drawdown"] = (
        result["daily_value"] / result["daily_value"].cummax() - 1
    )

    return result
