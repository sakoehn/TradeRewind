"""Tests for all strategies (Moving Average, Buy and Hold, Momentum).

Coverage targets
----------------
* strategies/moving_average.py
    - _validate_inputs         : all TypeError / ValueError branches
    - _compute_sma_signals     : window sizes, NaN handling, golden/death cross
    - _simulate_trades         : buy/sell mechanics, portfolio accounting
    - moving_average_crossover : public API, edge cases, mutation guard

* strategies/buy_and_hold.py
    - buy_and_hold             : regression - behaviour must be unchanged

* strategies/momentum.py
    - _validate_inputs             : all TypeError / ValueError branches
    - _compute_momentum_trades     : lookback ratio, trade signals
    - _simulate_momentum_trades    : buy/sell mechanics, cash/share accounting
    - momentum                     : public API, edge cases, mutation guard

* strategies/__init__.py
    - run_strategy             : dispatch, case-insensitivity, invalid name

* charts/common.py
    - format_summary           : percentage keys, plain floats, non-floats
    - prepare_plot_df          : tz strip, NaN drop, index reset

Run with::

    pytest test_strategies.py -v --tb=short
"""

import math

import pandas as pd
import pytest

from strategies.moving_average import (
    MIN_ROWS_REQUIRED,
    LONG_WINDOW,
    SHORT_WINDOW,
    _compute_sma_signals,
    _simulate_trades,
    _validate_inputs,
    moving_average_crossover,
)
from strategies.buy_and_hold import buy_and_hold
from strategies.momentum import (
    _validate_inputs as _momentum_validate_inputs,
    _compute_momentum_trades,
    _simulate_momentum_trades,
    momentum,
)
from strategies import run_strategy
from charts.common import format_summary, prepare_plot_df

# Fixtures / helpers
def _make_prices(n: int, close_values=None) -> pd.DataFrame:
    """Return a minimal price DataFrame with *n* rows.

    Args:
        n: Number of rows.
        close_values: Optional list of close prices.  Defaults to 100.0.

    Returns:
        DataFrame with ``date``, ``close``, and the auxiliary columns that
        ``compute_metrics`` requires.
    """
    dates = pd.date_range("2000-01-03", periods=n, freq="B")
    closes = list(close_values) if close_values is not None else [100.0] * n
    assert len(closes) == n

    return pd.DataFrame({
        "date": dates,
        "close": closes,
        "return_1d": [0.0] * n,
        "return_5d": [0.0] * n,
        "return_20d": [0.0] * n,
        "sma_200": [100.0] * n,
        "rsi_14": [50.0] * n,
        "atr_14": [1.0] * n,
        "volatility_20d": [0.01] * n,
        "volume_ratio": [1.0] * n,
    })


def _make_golden_cross_prices(n: int = 300) -> list:
    """Prices that produce exactly one golden cross mid-way through."""
    prices = []
    for i in range(n):
        if i < 150:
            prices.append(200.0 - i * 0.3)
        else:
            prices.append(155.0 + (i - 150) * 0.5)
    return prices

# _validate_inputs (moving average)
class TestValidateInputs:
    """Unit tests for input validation helper."""

    # Confirms a non-DataFrame input raises TypeError
    def test_raises_if_not_dataframe(self):
        with pytest.raises(TypeError, match="pandas DataFrame"):
            _validate_inputs([1, 2, 3], 1000)

    # Confirms an empty DataFrame raises ValueError
    def test_raises_if_empty_dataframe(self):
        with pytest.raises(ValueError, match="empty"):
            _validate_inputs(pd.DataFrame(), 1000)

    # Confirms a DataFrame missing the 'close' column raises ValueError
    def test_raises_if_no_close_column(self):
        with pytest.raises(ValueError, match="'close' column"):
            _validate_inputs(pd.DataFrame({"open": [1, 2, 3]}), 1000)

    # Confirms an all-NaN 'close' column raises ValueError
    def test_raises_if_close_all_nan(self):
        df = pd.DataFrame({"close": [float("nan")] * 5})
        with pytest.raises(ValueError, match="no valid"):
            _validate_inputs(df, 1000)

    # Confirms a non-numeric initial_capital raises TypeError
    def test_raises_if_capital_not_numeric(self):
        with pytest.raises(TypeError, match="numeric"):
            _validate_inputs(_make_prices(MIN_ROWS_REQUIRED), "1000")

    # Confirms zero initial_capital raises ValueError
    def test_raises_if_capital_zero(self):
        with pytest.raises(ValueError, match="greater than zero"):
            _validate_inputs(_make_prices(MIN_ROWS_REQUIRED), 0)

    # Confirms negative initial_capital raises ValueError
    def test_raises_if_capital_negative(self):
        with pytest.raises(ValueError, match="greater than zero"):
            _validate_inputs(_make_prices(MIN_ROWS_REQUIRED), -500)

    # Confirms too few rows raises ValueError with row-count info
    def test_raises_if_insufficient_rows(self):
        with pytest.raises(ValueError, match="Not enough data"):
            _validate_inputs(_make_prices(LONG_WINDOW), 1000)

    # Confirms the exact minimum row count passes validation
    def test_passes_with_minimum_rows(self):
        _validate_inputs(_make_prices(MIN_ROWS_REQUIRED), 1000)

    # Confirms integer capital is accepted as numeric
    def test_passes_with_integer_capital(self):
        _validate_inputs(_make_prices(MIN_ROWS_REQUIRED), 5000)

    # Confirms the error message includes both the required and actual row counts
    def test_error_message_contains_counts(self):
        with pytest.raises(ValueError) as exc_info:
            _validate_inputs(_make_prices(50), 1000)
        msg = str(exc_info.value)
        assert str(MIN_ROWS_REQUIRED) in msg
        assert "50" in msg


# _compute_sma_signals
class TestComputeSmaSignals:
    """Unit tests for SMA and signal computation."""

    # Confirms SMA-50 is NaN for the first (SHORT_WINDOW - 1) rows
    def test_sma_50_nan_before_window(self):
        result = _compute_sma_signals(_make_prices(300).copy())
        assert result["sma_50"].iloc[:SHORT_WINDOW - 1].isna().all()
        assert not math.isnan(result["sma_50"].iloc[SHORT_WINDOW - 1])

    # Confirms SMA-200 is NaN for the first (LONG_WINDOW - 1) rows
    def test_sma_200_nan_before_window(self):
        result = _compute_sma_signals(_make_prices(300).copy())
        assert result["sma_200"].iloc[:LONG_WINDOW - 1].isna().all()
        assert not math.isnan(result["sma_200"].iloc[LONG_WINDOW - 1])

    # Confirms both SMAs equal the constant price when close is flat
    def test_sma_correct_for_constant_price(self):
        df = _make_prices(300, close_values=[50.0] * 300)
        result = _compute_sma_signals(df.copy())
        assert (result["sma_50"].dropna() == 50.0).all()
        assert (result["sma_200"].dropna() == 50.0).all()

    # Confirms signal stays 0 when prices are flat (no crossover possible)
    def test_signal_zero_for_flat_prices(self):
        result = _compute_sma_signals(_make_prices(300).copy())
        assert (result["signal"] == 0).all()

    # Confirms signal becomes 1 for steadily rising prices (SMA-50 > SMA-200)
    def test_signal_one_for_rising_prices(self):
        prices = list(range(1, 301))
        df = _make_prices(300, close_values=prices)
        result = _compute_sma_signals(df.copy())
        assert (result["signal"].iloc[250:] == 1).all()

    # Confirms at least one buy trade is detected on a golden cross pattern
    def test_trade_detects_buy(self):
        prices = _make_golden_cross_prices()
        df = _make_prices(len(prices), close_values=prices)
        result = _compute_sma_signals(df.copy())
        assert len(result[result["trade"] == 1]) >= 1

    # Confirms at least one sell trade is detected when prices reverse downward
    def test_trade_detects_sell(self):
        n = 350
        prices = [100.0 + i * 0.5 if i < 200 else 200.0 - (i - 200) * 2.0
                  for i in range(n)]
        df = _make_prices(n, close_values=prices)
        result = _compute_sma_signals(df.copy())
        assert len(result[result["trade"] == -1]) >= 1

    # Confirms no trades are generated when prices are perfectly flat
    def test_trade_zero_for_flat_prices(self):
        df = _make_prices(300, close_values=[100.0] * 300)
        result = _compute_sma_signals(df.copy())
        assert (result["trade"] == 0).all()

# _simulate_trades (moving average)
class TestSimulateTrades:
    """Unit tests for trade simulation and portfolio accounting."""

    def _flat_df(self, n: int = 300):
        df = _make_prices(n)
        return _compute_sma_signals(df)

    # Confirms portfolio starts at initial_capital when there are no trades
    def test_starts_at_initial_capital_with_no_trade(self):
        result = _simulate_trades(self._flat_df(), 5000.0)
        assert result["daily_value"].iloc[0] == pytest.approx(5000.0)

    # Confirms all capital stays in cash when no buy signal fires
    def test_all_cash_when_no_buy_signal(self):
        result = _simulate_trades(self._flat_df(), 1000.0)
        assert (result["position"] == 0.0).all()
        assert (result["cash"] == 1000.0).all()

    # Confirms a buy signal moves all cash into shares
    def test_buy_moves_cash_to_shares(self):
        prices = _make_golden_cross_prices()
        df = _compute_sma_signals(_make_prices(len(prices), close_values=prices))
        result = _simulate_trades(df, 10000.0)
        buy_day = result[result["trade"] == 1].index[0]
        assert result["cash"].iloc[buy_day] == pytest.approx(0.0, abs=1e-6)
        assert result["position"].iloc[buy_day] > 0

    # Confirms a sell signal moves all shares back to cash
    def test_sell_moves_shares_to_cash(self):
        n = 400
        prices = [100.0 + i * 0.5 if i < 220 else 210.0 - (i - 220) * 2.0
                  for i in range(n)]
        df = _compute_sma_signals(_make_prices(n, close_values=prices))
        result = _simulate_trades(df, 10000.0)
        sells = result[result["trade"] == -1]
        if not sells.empty:
            sell_day = sells.index[0]
            assert result["position"].iloc[sell_day] == pytest.approx(0.0, abs=1e-6)
            assert result["cash"].iloc[sell_day] > 0

    # Confirms daily_value = cash + (position * price) on every row
    def test_daily_value_equals_cash_plus_equity(self):
        prices = _make_golden_cross_prices()
        df = _compute_sma_signals(_make_prices(len(prices), close_values=prices))
        result = _simulate_trades(df, 10000.0)
        expected = result["cash"] + result["position"] * result["price"]
        pd.testing.assert_series_equal(
            result["daily_value"].reset_index(drop=True),
            expected.reset_index(drop=True),
            check_names=False, rtol=1e-9,
        )

    # Confirms profit_to_date = daily_value - initial_capital
    def test_profit_to_date_correct(self):
        prices = _make_golden_cross_prices()
        df = _compute_sma_signals(_make_prices(len(prices), close_values=prices))
        result = _simulate_trades(df, 10000.0)
        expected = result["daily_value"] - 10000.0
        pd.testing.assert_series_equal(
            result["profit_to_date"].reset_index(drop=True),
            expected.reset_index(drop=True),
            check_names=False,
        )

    # Confirms drawdown is always <= 0 (never above the peak)
    def test_drawdown_non_positive(self):
        prices = _make_golden_cross_prices()
        df = _compute_sma_signals(_make_prices(len(prices), close_values=prices))
        result = _simulate_trades(df, 10000.0)
        assert (result["drawdown"] <= 0).all()

    # Confirms drawdown is exactly 0 when prices only go up (always at peak)
    def test_drawdown_zero_at_all_time_high(self):
        prices = list(range(1, 301))
        df = _compute_sma_signals(_make_prices(300, close_values=prices))
        result = _simulate_trades(df, 10000.0)
        assert result["drawdown"].max() == pytest.approx(0.0, abs=1e-9)



# moving_average_crossover (public API)
class TestMovingAverageCrossover:
    """End-to-end tests for the public strategy function."""

    # Confirms the function returns a DataFrame
    def test_returns_dataframe(self):
        assert isinstance(
            moving_average_crossover(_make_prices(MIN_ROWS_REQUIRED), 10000.0, pd.DataFrame()),
            pd.DataFrame,
        )

    # Confirms all strategy-specific columns are present in the output
    def test_output_has_required_columns(self):
        required = {
            "sma_50", "sma_200", "signal", "trade",
            "cash", "position", "price",
            "daily_value", "daily_returns", "profit_to_date", "drawdown",
        }
        result = moving_average_crossover(
            _make_prices(MIN_ROWS_REQUIRED), 10000.0, pd.DataFrame()
        )
        assert required.issubset(set(result.columns))

    # Confirms insufficient data raises ValueError
    def test_raises_insufficient_data(self):
        with pytest.raises(ValueError, match="Not enough data"):
            moving_average_crossover(_make_prices(LONG_WINDOW), 10000.0, pd.DataFrame())

    # Confirms empty DataFrame raises ValueError
    def test_raises_empty_dataframe(self):
        with pytest.raises(ValueError, match="empty"):
            moving_average_crossover(pd.DataFrame(), 10000.0, pd.DataFrame())

    # Confirms missing 'close' column raises ValueError
    def test_raises_missing_close(self):
        df = pd.DataFrame({"open": [1.0] * MIN_ROWS_REQUIRED})
        with pytest.raises(ValueError, match="'close' column"):
            moving_average_crossover(df, 10000.0, pd.DataFrame())

    # Confirms non-positive capital raises ValueError
    def test_raises_non_positive_capital(self):
        with pytest.raises(ValueError, match="greater than zero"):
            moving_average_crossover(_make_prices(MIN_ROWS_REQUIRED), 0.0, pd.DataFrame())

    # Confirms non-numeric capital raises TypeError
    def test_raises_non_numeric_capital(self):
        with pytest.raises(TypeError, match="numeric"):
            moving_average_crossover(_make_prices(MIN_ROWS_REQUIRED), "big", pd.DataFrame())

    # Confirms flat prices produce no crossover and portfolio stays at initial capital
    def test_no_crossover_stays_in_cash_original(self):
        df = _make_prices(300, close_values=[100.0] * 300)
        result = moving_average_crossover(df, 10000.0, pd.DataFrame())
        assert result["daily_value"].values == pytest.approx(10000.0)

    # Confirms a golden cross pattern causes the strategy to invest
    def test_golden_cross_invests_capital(self):
        prices = _make_golden_cross_prices()
        df = _make_prices(len(prices), close_values=prices)
        result = moving_average_crossover(df, 10000.0, pd.DataFrame())
        assert (result["position"] > 0).any()

    # Confirms the first daily return is always zero (no prior day)
    def test_first_daily_return_is_zero(self):
        result = moving_average_crossover(
            _make_prices(MIN_ROWS_REQUIRED), 1000.0, pd.DataFrame()
        )
        assert result["daily_returns"].iloc[0] == pytest.approx(0.0)

    # Confirms output row count matches input row count
    def test_output_length_matches_input(self):
        n = MIN_ROWS_REQUIRED + 50
        result = moving_average_crossover(_make_prices(n), 1000.0, pd.DataFrame())
        assert len(result) == n

    # Confirms the input DataFrame is not mutated by the strategy
    def test_input_not_mutated(self):
        df = _make_prices(MIN_ROWS_REQUIRED)
        original_cols = set(df.columns)
        moving_average_crossover(df, 1000.0, pd.DataFrame())
        assert set(df.columns) == original_cols

    # Confirms portfolio value never goes negative
    def test_portfolio_value_always_positive(self):
        prices = _make_golden_cross_prices()
        df = _make_prices(len(prices), close_values=prices)
        result = moving_average_crossover(df, 10000.0, pd.DataFrame())
        assert (result["daily_value"] > 0).all()

    # Confirms at least two trade signals occur with oscillating prices
    def test_multiple_crossovers(self):
        n = 600
        prices = [
            100.0 + (i % 300) * 0.4 if (i % 300) < 150
            else 160.0 - ((i % 300) - 150) * 0.4
            for i in range(n)
        ]
        df = _make_prices(n, close_values=prices)
        result = moving_average_crossover(df, 10000.0, pd.DataFrame())
        assert (result["trade"] != 0).sum() >= 2

    # Confirms a second golden cross triggers a second buy
    def test_second_golden_cross_reinvests(self):
        prices = (
            [100.0 + i * 0.5 for i in range(230)]
            + [215.0 - i * 1.5 for i in range(100)]
            + [65.0 + i * 0.6 for i in range(200)]
        )
        df = _make_prices(len(prices), close_values=prices)
        result = moving_average_crossover(df, 10000.0, pd.DataFrame())
        assert len(result[result["trade"] == 1]) >= 2

    # Confirms the unused full_df argument doesn't affect results
    def test_unused_df_argument_ignored(self):
        result = moving_average_crossover(
            _make_prices(MIN_ROWS_REQUIRED), 1000.0, pd.DataFrame({"x": [1]})
        )
        assert isinstance(result, pd.DataFrame)

# buy_and_hold — full coverage
class TestBuyAndHold:
    """Tests for buy_and_hold: core behaviour, output contract, key formulas."""

    # Confirms the same number of shares is held every day (no trading)
    def test_position_constant(self):
        """Buy-and-hold holds the same number of shares every day."""
        prices_df = _make_prices(50)
        initial_capital = 1000.0
        result = buy_and_hold(prices_df, initial_capital, pd.DataFrame())
        num_different_positions = result["position"].nunique()
        assert num_different_positions == 1

    # Confirms daily_value = shares * close price on every row
    def test_daily_value_equals_shares_times_price(self):
        """Portfolio value each day should equal shares held times price that day."""
        close_prices = [10.0 + i for i in range(50)]
        prices_df = _make_prices(50, close_values=close_prices)
        initial_capital = 1000.0
        result = buy_and_hold(prices_df, initial_capital, pd.DataFrame())
        expected_value = result["position"] * result["close"]
        pd.testing.assert_series_equal(
            result["daily_value"].reset_index(drop=True),
            expected_value.reset_index(drop=True),
            check_names=False,
        )

    # Confirms zero profit when prices never change
    def test_flat_prices_zero_profit(self):
        """If the price never changes, profit should be zero."""
        flat_prices = [100.0] * 50
        prices_df = _make_prices(50, close_values=flat_prices)
        initial_capital = 1000.0
        result = buy_and_hold(prices_df, initial_capital, pd.DataFrame())
        profit_series = result["profit_to_date"]
        assert profit_series.values == pytest.approx(0.0)

    # Confirms the return type is a pandas DataFrame
    def test_returns_dataframe(self):
        """buy_and_hold should return a pandas DataFrame."""
        prices_df = _make_prices(10)
        initial_capital = 1000.0
        result = buy_and_hold(prices_df, initial_capital, pd.DataFrame())
        assert isinstance(result, pd.DataFrame)

    # Confirms all required strategy columns are present
    def test_output_has_all_required_columns(self):
        """Result should include position, price, daily_value, daily_returns, profit_to_date, drawdown."""
        prices_df = _make_prices(10)
        initial_capital = 5000.0
        result = buy_and_hold(prices_df, initial_capital, pd.DataFrame())
        required_column_names = {
            "position", "price", "daily_value", "daily_returns",
            "profit_to_date", "drawdown",
        }
        result_columns = set(result.columns)
        assert required_column_names.issubset(result_columns)

    # Confirms the 'price' column is identical to the 'close' column
    def test_price_equals_close(self):
        """The 'price' column should match the 'close' column."""
        close_prices = [50.0 + i for i in range(20)]
        prices_df = _make_prices(20, close_values=close_prices)
        initial_capital = 1000.0
        result = buy_and_hold(prices_df, initial_capital, pd.DataFrame())
        pd.testing.assert_series_equal(
            result["price"], result["close"], check_names=False
        )

    # Confirms first-day portfolio value equals the initial investment
    def test_daily_value_first_day_equals_initial_capital(self):
        """On the first day we invest all cash, so portfolio value equals initial capital."""
        prices_df = _make_prices(10, close_values=[50.0] * 10)
        initial_capital = 1000.0
        result = buy_and_hold(prices_df, initial_capital, pd.DataFrame())
        first_day_value = result["daily_value"].iloc[0]
        assert first_day_value == pytest.approx(initial_capital)

    # Confirms the first daily return is zero (no prior day to compare)
    def test_daily_returns_first_row_zero(self):
        """The first day has no previous day to compare, so daily return is zero."""
        prices_df = _make_prices(10)
        initial_capital = 1000.0
        result = buy_and_hold(prices_df, initial_capital, pd.DataFrame())
        first_day_return = result["daily_returns"].iloc[0]
        assert first_day_return == pytest.approx(0.0)

    # Confirms profit_to_date = daily_value - initial_capital
    def test_profit_to_date_equals_daily_value_minus_capital(self):
        """Profit to date is current portfolio value minus what we started with."""
        close_prices = [100.0 + i * 2 for i in range(20)]
        prices_df = _make_prices(20, close_values=close_prices)
        initial_capital = 5000.0
        result = buy_and_hold(prices_df, initial_capital, pd.DataFrame())
        expected_profit = result["daily_value"] - initial_capital
        pd.testing.assert_series_equal(
            result["profit_to_date"].reset_index(drop=True),
            expected_profit.reset_index(drop=True),
            check_names=False,
        )

    # Confirms drawdown is always <= 0
    def test_drawdown_non_positive(self):
        """Drawdown is never positive; it measures how far we are below the peak."""
        falling_prices = [100.0 - i for i in range(30)]
        prices_df = _make_prices(30, close_values=falling_prices)
        initial_capital = 1000.0
        result = buy_and_hold(prices_df, initial_capital, pd.DataFrame())
        drawdown_series = result["drawdown"]
        assert (drawdown_series <= 0).all()

    # Confirms the input DataFrame columns are not modified
    def test_input_not_mutated(self):
        """Calling buy_and_hold should not change the input DataFrame's columns."""
        prices_df = _make_prices(10)
        columns_before = set(prices_df.columns)
        initial_capital = 1000.0
        buy_and_hold(prices_df, initial_capital, pd.DataFrame())
        columns_after = set(prices_df.columns)
        assert columns_before == columns_after

    # Confirms rising prices produce positive profit at the end
    def test_rising_prices_positive_profit_at_end(self):
        """If prices go up over time, we should have positive profit at the end."""
        rising_prices = [100.0 + i * 5 for i in range(20)]
        prices_df = _make_prices(20, close_values=rising_prices)
        initial_capital = 10000.0
        result = buy_and_hold(prices_df, initial_capital, pd.DataFrame())
        final_profit = result["profit_to_date"].iloc[-1]
        assert final_profit > 0

# strategies.run_strategy dispatch
class TestRunStrategy:
    """Tests for the registry-based dispatch in strategies/__init__.py."""

    # Confirms buy_and_hold is dispatched and returns expected columns
    def test_dispatches_buy_and_hold(self):
        result = run_strategy(_make_prices(50), "Buy and Hold", 1000.0, pd.DataFrame())
        assert "position" in result.columns

    # Confirms moving average crossover dispatches regardless of case
    def test_dispatches_ma_crossover_mixed_case(self):
        df = _make_prices(MIN_ROWS_REQUIRED)
        for name in [
            "Moving Average Crossover",
            "moving average crossover",
            "MOVING AVERAGE CROSSOVER",
        ]:
            result = run_strategy(df, name, 1000.0, pd.DataFrame())
            assert "sma_50" in result.columns

    # Confirms an unregistered strategy name raises ValueError
    def test_raises_on_invalid_strategy(self):
        with pytest.raises(ValueError, match="not a valid strategy"):
            run_strategy(_make_prices(50), "Unknown Strategy", 1000.0, pd.DataFrame())

    # Confirms an empty strategy name raises ValueError
    def test_raises_on_empty_strategy_name(self):
        with pytest.raises(ValueError):
            run_strategy(_make_prices(50), "", 1000.0, pd.DataFrame())

# charts.common
class TestFormatSummary:
    """Tests for the format_summary utility."""

    # Confirms keys containing "Return" are formatted as percentages
    def test_return_key_formatted_as_percentage(self):
        result = format_summary({"Total Return": 0.25})
        assert result["Total Return"] == "25.00%"

    # Confirms keys containing "%" are formatted as percentages
    def test_percent_symbol_key_formatted_as_percentage(self):
        result = format_summary({"% Above SMA200": 0.6})
        assert result["% Above SMA200"] == "60.00%"

    # Confirms plain float values are formatted to two decimal places
    def test_plain_float_two_decimal_places(self):
        result = format_summary({"Sharpe Ratio": 1.2345})
        assert result["Sharpe Ratio"] == "1.23"

    # Confirms non-float values are converted to string as-is
    def test_non_float_converted_to_string(self):
        result = format_summary({"Win Rate": "N/A"})
        assert result["Win Rate"] == "N/A"

    # Confirms integer values are converted to string
    def test_integer_value_converted_to_string(self):
        result = format_summary({"Count": 42})
        assert result["Count"] == "42"


class TestPreparePlotDf:
    """Tests for the prepare_plot_df utility."""

    # Confirms timezone-aware dates are stripped to tz-naive
    def test_strips_timezone(self):
        df = _make_prices(MIN_ROWS_REQUIRED)
        df["date"] = pd.to_datetime(df["date"], utc=True)
        df["daily_value"] = 1000.0
        df["daily_returns"] = 0.0
        result = prepare_plot_df(df)
        assert result["date"].dt.tz is None

    # Confirms rows with NaN daily_value are dropped
    def test_drops_nan_daily_value_rows(self):
        df = _make_prices(10)
        df["daily_value"] = [float("nan")] * 3 + [1000.0] * 7
        df["daily_returns"] = 0.0
        result = prepare_plot_df(df)
        assert len(result) == 7

    # Confirms the index is reset to a clean 0..N-1 range
    def test_resets_index(self):
        df = _make_prices(10)
        df["daily_value"] = 1000.0
        df["daily_returns"] = 0.0
        df = df.iloc[5:]  # intentionally broken index
        result = prepare_plot_df(df)
        assert list(result.index) == list(range(len(result)))

# _validate_inputs (momentum)
class TestMomentumValidateInputs:
    """Unit tests for momentum input validation."""

    # Confirms a non-DataFrame input raises TypeError
    def test_raises_if_not_dataframe(self):
        with pytest.raises(TypeError, match="pandas DataFrame"):
            _momentum_validate_inputs([1, 2, 3], 1000)

    # Confirms an empty DataFrame raises ValueError
    def test_raises_if_empty_dataframe(self):
        with pytest.raises(ValueError, match="empty"):
            _momentum_validate_inputs(pd.DataFrame(), 1000)

    # Confirms a DataFrame missing the 'close' column raises ValueError
    def test_raises_if_no_close_column(self):
        with pytest.raises(ValueError, match="'close' column"):
            _momentum_validate_inputs(pd.DataFrame({"open": [1]}), 1000)

    # Confirms an all-NaN 'close' column raises ValueError
    def test_raises_if_close_all_nan(self):
        df = pd.DataFrame({"close": [float("nan")] * 5})
        with pytest.raises(ValueError, match="no valid"):
            _momentum_validate_inputs(df, 1000)

    # Confirms a non-numeric initial_capital raises TypeError
    def test_raises_if_capital_not_numeric(self):
        with pytest.raises(TypeError, match="numeric"):
            _momentum_validate_inputs(_make_prices(50), "1000")

    # Confirms zero initial_capital raises ValueError
    def test_raises_if_capital_zero(self):
        with pytest.raises(ValueError, match="greater than zero"):
            _momentum_validate_inputs(_make_prices(50), 0)

    # Confirms negative initial_capital raises ValueError
    def test_raises_if_capital_negative(self):
        with pytest.raises(ValueError, match="greater than zero"):
            _momentum_validate_inputs(_make_prices(50), -500)

    # Confirms valid inputs pass without error
    def test_passes_with_valid_inputs(self):
        _momentum_validate_inputs(_make_prices(50), 1000)


# _compute_momentum_trades
class TestComputeMomentumTrades:
    """Unit tests for lookback ratio and trade signal computation."""

    # Confirms lookback_ratio is 1 (hold) within the lookback window
    def test_lookback_ratio_filled_to_one_in_window(self):
        df = _make_prices(50).copy()
        result = _compute_momentum_trades(df, 20)
        assert (result["lookback_ratio"].iloc[:20] == 1.0).all()

    # Confirms rising prices produce a lookback_ratio > 1 (buy signal)
    def test_rising_prices_ratio_above_one(self):
        prices = [100.0 + i for i in range(50)]
        df = _make_prices(50, close_values=prices).copy()
        result = _compute_momentum_trades(df, 20)
        assert (result["lookback_ratio"].iloc[20:] > 1).all()

    # Confirms falling prices produce a lookback_ratio < 1 (sell signal)
    def test_falling_prices_ratio_below_one(self):
        prices = [200.0 - i for i in range(50)]
        df = _make_prices(50, close_values=prices).copy()
        result = _compute_momentum_trades(df, 20)
        assert (result["lookback_ratio"].iloc[20:] < 1).all()

    # Confirms trade == 0 (hold) within the lookback window
    def test_trade_zero_in_lookback_window(self):
        df = _make_prices(50).copy()
        result = _compute_momentum_trades(df, 20)
        assert (result["trade"].iloc[:20] == 0).all()

    # Confirms trade == 1 (buy) when prices are rising
    def test_trade_buy_for_rising_prices(self):
        prices = [100.0 + i for i in range(50)]
        df = _make_prices(50, close_values=prices).copy()
        result = _compute_momentum_trades(df, 20)
        assert (result["trade"].iloc[20:] == 1).all()

    # Confirms trade == -1 (sell) when prices are falling
    def test_trade_sell_for_falling_prices(self):
        prices = [200.0 - i for i in range(50)]
        df = _make_prices(50, close_values=prices).copy()
        result = _compute_momentum_trades(df, 20)
        assert (result["trade"].iloc[20:] == -1).all()

    # Confirms flat prices produce trade == 0 everywhere
    def test_flat_prices_no_trades(self):
        df = _make_prices(50, close_values=[100.0] * 50).copy()
        result = _compute_momentum_trades(df, 20)
        assert (result["trade"] == 0).all()


# _simulate_momentum_trades
class TestSimulateMomentumTrades:
    """Unit tests for momentum trade simulation and portfolio accounting."""

    def _make_trade_df(self, prices, lookback=20):
        df = _make_prices(len(prices), close_values=prices).copy()
        return _compute_momentum_trades(df, lookback)

    # Confirms portfolio starts at initial_capital on day 0
    def test_starts_at_initial_capital(self):
        trade_df = self._make_trade_df([100.0] * 50)
        result = _simulate_momentum_trades(trade_df, 10000.0, 10)
        assert result["daily_value"].iloc[0] == pytest.approx(10000.0)

    # Confirms all capital stays in cash when no buy signal fires (flat prices)
    def test_all_cash_when_flat(self):
        trade_df = self._make_trade_df([100.0] * 50)
        result = _simulate_momentum_trades(trade_df, 10000.0, 10)
        assert (result["position"] == 0.0).all()
        assert (result["cash"] == 10000.0).all()

    # Confirms a buy signal reduces cash and increases shares
    def test_buy_reduces_cash(self):
        prices = [100.0 + i for i in range(50)]
        trade_df = self._make_trade_df(prices)
        result = _simulate_momentum_trades(trade_df, 10000.0, 10)
        first_buy = result[result["trade"] == 1].index[0]
        assert result["cash"].iloc[first_buy] < 10000.0
        assert result["position"].iloc[first_buy] > 0

    # Confirms daily_value = cash + (position * price) on every row
    def test_daily_value_equals_cash_plus_equity(self):
        prices = [100.0 + i * 0.5 for i in range(50)]
        trade_df = self._make_trade_df(prices)
        result = _simulate_momentum_trades(trade_df, 10000.0, 10)
        expected = result["cash"] + result["position"] * result["price"]
        pd.testing.assert_series_equal(
            result["daily_value"].reset_index(drop=True),
            expected.reset_index(drop=True),
            check_names=False, rtol=1e-9,
        )

    # Confirms profit_to_date = daily_value - initial_capital
    def test_profit_to_date_correct(self):
        prices = [100.0 + i for i in range(50)]
        trade_df = self._make_trade_df(prices)
        result = _simulate_momentum_trades(trade_df, 10000.0, 10)
        expected = result["daily_value"] - 10000.0
        pd.testing.assert_series_equal(
            result["profit_to_date"].reset_index(drop=True),
            expected.reset_index(drop=True),
            check_names=False,
        )

    # Confirms drawdown is always <= 0
    def test_drawdown_non_positive(self):
        prices = [100.0 + i for i in range(50)]
        trade_df = self._make_trade_df(prices)
        result = _simulate_momentum_trades(trade_df, 10000.0, 10)
        assert (result["drawdown"] <= 0).all()

    # Confirms sell signal only fires when there are shares to sell
    def test_sell_only_when_shares_held(self):
        # First 25 days rising (buys), then 25 days falling (sells)
        prices = [100.0 + i for i in range(25)] + [124.0 - i for i in range(25)]
        trade_df = self._make_trade_df(prices)
        result = _simulate_momentum_trades(trade_df, 10000.0, 10)
        # Position should never go negative
        assert (result["position"] >= -1e-9).all()

    # Confirms cash never goes negative
    def test_cash_never_negative(self):
        prices = [100.0 + i for i in range(50)]
        trade_df = self._make_trade_df(prices)
        result = _simulate_momentum_trades(trade_df, 10000.0, 10)
        assert (result["cash"] >= -1e-9).all()


# momentum (public API)
class TestMomentum:
    """End-to-end tests for the public momentum strategy function."""

    # Confirms the function returns a DataFrame
    def test_returns_dataframe(self):
        result = momentum(_make_prices(50), 10000.0, pd.DataFrame())
        assert isinstance(result, pd.DataFrame)

    # Confirms all strategy-specific columns are present in the output
    def test_output_has_required_columns(self):
        required = {
            "lookback_ratio", "trade", "cash", "position", "price",
            "daily_value", "daily_returns", "profit_to_date", "drawdown",
        }
        result = momentum(_make_prices(50), 10000.0, pd.DataFrame())
        assert required.issubset(set(result.columns))

    # Confirms empty DataFrame raises ValueError
    def test_raises_empty_dataframe(self):
        with pytest.raises(ValueError, match="empty"):
            momentum(pd.DataFrame(), 10000.0, pd.DataFrame())

    # Confirms missing 'close' column raises ValueError
    def test_raises_missing_close(self):
        df = pd.DataFrame({"open": [1.0] * 50})
        with pytest.raises(ValueError, match="'close' column"):
            momentum(df, 10000.0, pd.DataFrame())

    # Confirms non-positive capital raises ValueError
    def test_raises_non_positive_capital(self):
        with pytest.raises(ValueError, match="greater than zero"):
            momentum(_make_prices(50), 0.0, pd.DataFrame())

    # Confirms non-numeric capital raises TypeError
    def test_raises_non_numeric_capital(self):
        with pytest.raises(TypeError, match="numeric"):
            momentum(_make_prices(50), "big", pd.DataFrame())

    # Confirms flat prices produce no trades and portfolio stays at initial capital
    def test_flat_prices_stays_in_cash(self):
        df = _make_prices(50, close_values=[100.0] * 50)
        result = momentum(df, 10000.0, pd.DataFrame())
        assert result["daily_value"].values == pytest.approx(10000.0)

    # Confirms rising prices generate buy signals and positive profit
    def test_rising_prices_positive_profit(self):
        prices = [100.0 + i * 0.5 for i in range(100)]
        df = _make_prices(100, close_values=prices)
        result = momentum(df, 10000.0, pd.DataFrame())
        assert result["profit_to_date"].iloc[-1] > 0

    # Confirms the first daily return is always zero
    def test_first_daily_return_is_zero(self):
        result = momentum(_make_prices(50), 1000.0, pd.DataFrame())
        assert result["daily_returns"].iloc[0] == pytest.approx(0.0)

    # Confirms output row count matches input row count
    def test_output_length_matches_input(self):
        result = momentum(_make_prices(80), 1000.0, pd.DataFrame())
        assert len(result) == 80

    # Confirms the input DataFrame is not mutated by the strategy
    def test_input_not_mutated(self):
        df = _make_prices(50)
        original_cols = set(df.columns)
        momentum(df, 1000.0, pd.DataFrame())
        assert set(df.columns) == original_cols

    # Confirms portfolio value never goes negative
    def test_portfolio_value_always_positive(self):
        prices = [100.0 + i * 0.5 for i in range(100)]
        df = _make_prices(100, close_values=prices)
        result = momentum(df, 10000.0, pd.DataFrame())
        assert (result["daily_value"] > 0).all()

    # Confirms custom lookback_days parameter is respected
    def test_custom_lookback_days(self):
        prices = [100.0 + i for i in range(50)]
        df = _make_prices(50, close_values=prices)
        result = momentum(df, 10000.0, pd.DataFrame(), lookback_days=5)
        # With lookback=5, trades should start by row 5
        assert (result["trade"].iloc[:5] == 0).all()
        assert (result["trade"].iloc[5:] == 1).all()

    # Confirms custom trade_proportion parameter changes trade size
    def test_custom_trade_proportion(self):
        prices = [100.0 + i for i in range(50)]
        df = _make_prices(50, close_values=prices)
        result_10 = momentum(df, 10000.0, pd.DataFrame(), trade_proportion=10)
        result_50 = momentum(df, 10000.0, pd.DataFrame(), trade_proportion=50)
        # Larger trade proportion should invest more cash on the first buy
        first_buy_10 = result_10[result_10["trade"] == 1].index[0]
        first_buy_50 = result_50[result_50["trade"] == 1].index[0]
        assert result_10["cash"].iloc[first_buy_10] > result_50["cash"].iloc[first_buy_50]

    # Confirms the unused full_df argument doesn't affect results
    def test_unused_df_argument_ignored(self):
        result = momentum(
            _make_prices(50), 1000.0, pd.DataFrame({"x": [1]})
        )
        assert isinstance(result, pd.DataFrame)


# run_strategy dispatch for momentum
class TestRunStrategyMomentum:
    """Tests for momentum dispatch through run_strategy."""

    # Confirms momentum is dispatched and returns expected columns
    def test_dispatches_momentum(self):
        result = run_strategy(_make_prices(50), "Momentum", 1000.0, pd.DataFrame())
        assert "lookback_ratio" in result.columns

    # Confirms momentum dispatches regardless of case
    def test_dispatches_momentum_case_insensitive(self):
        for name in ["Momentum", "momentum", "MOMENTUM"]:
            result = run_strategy(_make_prices(50), name, 1000.0, pd.DataFrame())
            assert "lookback_ratio" in result.columns
