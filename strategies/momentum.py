"""Momentum strategy for TradeRewind.

Strategy rules
--------------
* Computes a lookback ratio: close[today] / close[today - lookback_days].
* If the ratio > 1 (price rising), buy ``trade_proportion`` % of
  ``initial_capital`` worth of shares (or whatever cash remains).
* If the ratio < 1 (price falling), sell ``trade_proportion`` % of
  ``initial_capital`` worth of shares (or whatever shares remain).
* If the ratio == 1 or is unavailable (within the lookback window),
  hold the current position.

Strategy contract
-----------------
The returned DataFrame contains every original column plus:

    lookback_ratio - close[t - lookback] / close[t], NaN filled to 1
    trade          - +1 buy, -1 sell, 0 hold
    cash           - uninvested cash balance each day
    position       - number of shares held each day
    price          - alias for ``close``
    daily_value    - total portfolio value (cash + equity)
    daily_returns  - percentage change in daily_value day-over-day
    profit_to_date - cumulative profit / loss vs. ``initial_capital``
    drawdown       - rolling drawdown from the running portfolio peak
"""

import numpy as np
import pandas as pd

# Default parameters (used when dispatched from the registry)
DEFAULT_LOOKBACK_DAYS: int = 20
DEFAULT_TRADE_PROPORTION: int = 10  # percent


def _validate_inputs(prices: pd.DataFrame, initial_capital: float) -> None:
    """Raise informative errors for bad inputs before any computation."""
    if not isinstance(prices, pd.DataFrame):
        raise TypeError("prices must be a pandas DataFrame.")
    if prices.empty:
        raise ValueError("prices DataFrame is empty.")
    if "close" not in prices.columns:
        raise ValueError("prices DataFrame must contain a 'close' column.")
    if prices["close"].dropna().empty:
        raise ValueError("The 'close' column contains no valid (non-NaN) data.")
    if not isinstance(initial_capital, (int, float)):
        raise TypeError("initial_capital must be a numeric value.")
    if initial_capital <= 0:
        raise ValueError("initial_capital must be greater than zero.")


def _compute_momentum_trades(price_df: pd.DataFrame, lookback_days: int) -> pd.DataFrame:
    """Add lookback_ratio and trade signal columns."""
    price_df["lookback_ratio"] = (
        price_df["close"] / price_df["close"].shift(lookback_days)
    )
    price_df["lookback_ratio"] = price_df["lookback_ratio"].fillna(1)

    price_df["trade"] = 0
    price_df.loc[price_df["lookback_ratio"] > 1, "trade"] = 1
    price_df.loc[price_df["lookback_ratio"] < 1, "trade"] = -1

    return price_df


def _simulate_momentum_trades(
    trade_df: pd.DataFrame,
    initial_capital: float,
    trade_proportion: int,
) -> pd.DataFrame:
    """Walk forward day-by-day, managing a cash + shares portfolio."""
    trade_amount = initial_capital * trade_proportion / 100
    row_count = len(trade_df)

    cash = np.zeros(row_count)
    shares = np.zeros(row_count)

    for i in range(row_count):
        trade = int(trade_df["trade"].iloc[i])
        close_price = float(trade_df["close"].iloc[i])

        cash_start = initial_capital if i == 0 else cash[i - 1]
        shares_start = 0.0 if i == 0 else shares[i - 1]

        share_inc = 0.0
        cash_inc = 0.0

        if trade == 1 and cash_start > 0:
            buy_amt = min(trade_amount, cash_start)
            share_inc = buy_amt / close_price
            cash_inc = -buy_amt
        elif trade == -1 and shares_start > 0:
            sell_amt = min(trade_amount, shares_start * close_price)
            share_inc = -sell_amt / close_price
            cash_inc = sell_amt

        cash[i] = cash_start + cash_inc
        shares[i] = shares_start + share_inc

    trade_df["cash"] = cash
    trade_df["position"] = shares
    trade_df["price"] = trade_df["close"]
    trade_df["daily_value"] = trade_df["cash"] + trade_df["position"] * trade_df["price"]
    trade_df["daily_returns"] = trade_df["daily_value"].pct_change().fillna(0)
    trade_df["profit_to_date"] = trade_df["daily_value"] - initial_capital
    trade_df["drawdown"] = trade_df["daily_value"] / trade_df["daily_value"].cummax() - 1

    return trade_df


def momentum(
    prices: pd.DataFrame,
    initial_capital: float,
    full_df: pd.DataFrame,  # pylint: disable=unused-argument
    lookback_days: int = DEFAULT_LOOKBACK_DAYS,
    trade_proportion: int = DEFAULT_TRADE_PROPORTION,
) -> pd.DataFrame:
    """Run the momentum back-test on a single stock.

    Args:
        prices: Date-filtered, single-stock DataFrame with a ``close`` column.
        initial_capital: Starting cash in dollars (must be > 0).
        full_df: Full combined dataset; unused but required by the strategy API.
        lookback_days: Number of days to look back for the momentum ratio.
        trade_proportion: Percent of initial_capital to trade per signal.

    Returns:
        Enriched DataFrame with strategy columns appended.
    """
    _validate_inputs(prices, initial_capital)

    result = prices.copy()
    result = result.reset_index(drop=True)
    result = _compute_momentum_trades(result, lookback_days)
    result = _simulate_momentum_trades(result, initial_capital, trade_proportion)

    return result
