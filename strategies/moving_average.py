"""Moving Average Crossover strategy for TradeRewind (50 / 200 day).

Strategy rules
--------------
* **Golden Cross** - SMA-50 crosses *above* SMA-200:
  buy all available cash at that day's closing price.
* **Death Cross** - SMA-50 crosses *below* SMA-200:
  liquidate all shares at that day's closing price, return to 100 % cash.
* Before the first 200 trading days the portfolio sits in cash (insufficient
  data to compute SMA-200).
* If the period ends while still invested, the open position is valued at the
  final closing price (no forced liquidation on the last day).

Strategy contract
-----------------
The returned DataFrame contains every original column plus:

    sma_50         - 50-day simple moving average of ``close``
    sma_200        - 200-day simple moving average of ``close``
    signal         - +1 (long / invested), 0 (flat / cash)
    trade          - +1 (buy), -1 (sell), 0 (no trade) on transition day
    cash           - uninvested cash balance each day
    position       - number of shares held each day
    price          - alias for ``close``
    daily_value    - total portfolio value (cash + equity)
    daily_returns  - percentage change in daily_value day-over-day
    profit_to_date - cumulative profit / loss vs. ``initial_capital``
    drawdown       - rolling drawdown from the running portfolio peak

Edge cases handled
------------------
* Insufficient rows (< 201 trading days) -> ``ValueError``
* Empty DataFrame                         -> ``ValueError``
* Missing ``close`` column                -> ``ValueError``
* All-NaN ``close`` values                -> ``ValueError``
* Non-numeric ``initial_capital``         -> ``TypeError``
* Non-positive ``initial_capital``        -> ``ValueError``
* No crossover in the date range          -> stays 100 % cash; metrics compute
* Multiple crossovers                     -> each transition is traded correctly
* Input DataFrame not mutated             -> strategy works on an internal copy
"""

import pandas as pd

# Module-level constants

SHORT_WINDOW: int = 50
LONG_WINDOW: int = 200
MIN_ROWS_REQUIRED: int = LONG_WINDOW + 1  # need at least one post-SMA-200 day

# Validation
def _validate_inputs(prices: pd.DataFrame, initial_capital: float) -> None:
    """Raise informative errors for bad inputs before any computation.

    Args:
        prices: Candidate price DataFrame supplied by the backtester.
        initial_capital: Starting cash in dollars.

    Raises:
        TypeError: If ``prices`` is not a DataFrame or ``initial_capital``
            is not a numeric type.
        ValueError: If ``prices`` is empty, missing the ``close`` column,
            has an all-NaN ``close``, has fewer rows than
            ``MIN_ROWS_REQUIRED``, or ``initial_capital`` is not positive.
    """
    if not isinstance(prices, pd.DataFrame):
        raise TypeError("prices must be a pandas DataFrame.")

    if prices.empty:
        raise ValueError("prices DataFrame is empty.")

    if "close" not in prices.columns:
        raise ValueError("prices DataFrame must contain a 'close' column.")

    if prices["close"].dropna().empty:
        raise ValueError(
            "The 'close' column contains no valid (non-NaN) data."
        )

    if not isinstance(initial_capital, (int, float)):
        raise TypeError("initial_capital must be a numeric value.")

    if initial_capital <= 0:
        raise ValueError("initial_capital must be greater than zero.")

    if len(prices) < MIN_ROWS_REQUIRED:
        raise ValueError(
            f"Not enough data for a {SHORT_WINDOW}/{LONG_WINDOW}-day crossover "
            f"strategy. Need at least {MIN_ROWS_REQUIRED} trading days; "
            f"got {len(prices)}. Consider widening your date range."
        )

# Signal computation
def _compute_sma_signals(price_df: pd.DataFrame) -> pd.DataFrame:
    """Add SMA columns and entry / exit signal columns to *price_df*.

    Columns added (in-place on a copy):

    * ``sma_50``  - 50-period rolling mean of ``close``
    * ``sma_200`` - 200-period rolling mean of ``close``
    * ``signal``  - 1 when SMA-50 > SMA-200 (both valid), else 0
    * ``trade``   - diff of ``signal``: +1 buy, -1 sell, 0 hold

    Args:
        price_df: Working copy with a ``close`` column.

    Returns:
        The same DataFrame with the four new columns appended.
    """
    price_df["sma_50"] = (
        price_df["close"]
        .rolling(window=SHORT_WINDOW, min_periods=SHORT_WINDOW)
        .mean()
    )
    price_df["sma_200"] = (
        price_df["close"]
        .rolling(window=LONG_WINDOW, min_periods=LONG_WINDOW)
        .mean()
    )

    # Default to flat (0); only go long when both SMAs are valid and SMA50 > SMA200
    price_df["signal"] = 0
    both_valid = price_df["sma_50"].notna() & price_df["sma_200"].notna()
    price_df.loc[both_valid & (price_df["sma_50"] > price_df["sma_200"]), "signal"] = 1

    # +1 -> new buy signal, -1 -> new sell signal, 0 -> unchanged
    price_df["trade"] = price_df["signal"].diff().fillna(0).astype(int)

    return price_df

# Trade simulation
def _simulate_trades(trade_df: pd.DataFrame, initial_capital: float) -> pd.DataFrame:
    """Walk forward day-by-day, managing a cash + shares portfolio.

    Execution rules:
    * On a **buy** day (``trade == +1``): invest all available cash at
      today's closing price.
    * On a **sell** day (``trade == -1``): liquidate all shares at today's
      closing price.
    * On all other days: hold current position unchanged.

    Args:
        trade_df: DataFrame with ``close``, ``signal``, and ``trade`` columns.
        initial_capital: Starting cash balance in dollars.

    Returns:
        The same DataFrame with ``cash``, ``position``, ``price``,
        ``daily_value``, ``daily_returns``, ``profit_to_date``, and
        ``drawdown`` columns appended.
    """
    cash: float = initial_capital
    shares: float = 0.0
    row_count = len(trade_df)

    cash_arr: list = [0.0] * row_count
    shares_arr: list = [0.0] * row_count

    for i in range(row_count):
        trade = int(trade_df["trade"].iloc[i])
        close_price = float(trade_df["close"].iloc[i])

        if trade == 1 and cash > 0:
            # Golden Cross: buy as many shares as cash allows
            shares = cash / close_price
            cash = 0.0

        elif trade == -1 and shares > 0:
            # Death Cross: liquidate entire position
            cash = shares * close_price
            shares = 0.0

        cash_arr[i] = cash
        shares_arr[i] = shares

    trade_df["cash"] = cash_arr
    trade_df["position"] = shares_arr
    trade_df["price"] = trade_df["close"]

    trade_df["daily_value"] = trade_df["cash"] + trade_df["position"] * trade_df["price"]
    trade_df["daily_returns"] = trade_df["daily_value"].pct_change().fillna(0)
    trade_df["profit_to_date"] = trade_df["daily_value"] - initial_capital
    trade_df["drawdown"] = trade_df["daily_value"] / trade_df["daily_value"].cummax() - 1

    return trade_df

# Public entry point
def moving_average_crossover(
    prices: pd.DataFrame,
    initial_capital: float,
    full_df: pd.DataFrame,  # pylint: disable=unused-argument  # kept for strategy API parity
) -> pd.DataFrame:
    """Run the 50/200-day SMA crossover back-test on a single stock.

    Args:
        prices: Date-filtered, single-stock DataFrame with a ``close``
            column.  Must contain at least ``MIN_ROWS_REQUIRED`` rows.
        initial_capital: Starting cash in dollars (must be > 0).
        full_df: Full combined dataset; unused but required by the strategy API
            so all strategies share the same call signature.

    Returns:
        Enriched DataFrame — all original columns plus the strategy columns
        listed in the module docstring.

    Raises:
        TypeError:  Wrong argument types (see ``_validate_inputs``).
        ValueError: Empty data, missing columns, bad capital, or
                    insufficient history (see ``_validate_inputs``).
    """
    _validate_inputs(prices, initial_capital)

    result = prices.copy()
    result = result.reset_index(drop=True)
    result = _compute_sma_signals(result)
    result = _simulate_trades(result, initial_capital)

    return result
